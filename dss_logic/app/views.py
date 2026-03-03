# ==============================================================================
# Standard Library Imports
# ==============================================================================
import base64
import csv
import io
import json
import logging
import os
import secrets
import string
from datetime import datetime, timedelta

# ==============================================================================
# Third-Party Imports
# ==============================================================================
import requests
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

# ==============================================================================
# Local Imports
# ==============================================================================
from .licensing import create_generate_license
from accounts.models import (
    Company,
    OrganizationWorkflow,
    OrganizationWorkflowUser,
    User,
    Workflow,
    WorkflowUser,
)
from .models import (
    Comment,
    Document,
    Logger,
    OtherSignersTable,
    Signer,
    SignerAnnotation,
    SMTPConfigs,
)
from .otp import *
from .serializers import (
    CompanyLogo,
    CompanySerializer,
    CompleteSerializer,
    RegisterAdminSerializer,
    RegisterCompanySerializer,
    RegisterSerializer,
    SMTPConfigsSerializer,
    UserAvatar,
    UserSerializer,
    CentralizedLoginSerializer
)
from .tasks import *
from .twilio import *
from .utilities import (
    generate_pdw,
    getUser,
    humanize_timestamp,
    send_email,
    send_email_newadmin,
    send_email_newcompany,
    send_email_newuser,
)

# ==============================================================================
# Module-Level Config
# ==============================================================================
logger = logging.getLogger(__name__)

base_url = settings.BASE_URL
dss_api = settings.DSS_API
frontend_url = settings.FRONTEND_URL
mailservice_url = "https://mailservice.alignsys.tech"

# Standard JSON headers for outbound DSS API requests
_DSS_HEADERS = {"Content-Type": "application/json"}


# ==============================================================================
# Shared Helpers
# ==============================================================================

def create_error_response(message, status_code=status.HTTP_400_BAD_REQUEST, extra_data=None):
    """Return a standardized DRF error Response."""
    data = {"error": message}
    if extra_data:
        data.update(extra_data)
    return Response(data, status=status_code)


def create_success_response(message, status_code=status.HTTP_200_OK, extra_data=None):
    """Return a standardized DRF success Response."""
    data = {"message": message}
    if extra_data:
        data.update(extra_data)
    return Response(data, status=status_code)


def _parse_date_range(request_data, use_query_params=False):
    """
    Extract and validate an ISO 8601 date range from either query params or POST body.

    Returns:
        (start_date, end_date) — both timezone-aware datetime objects.

    Raises:
        ValueError: if dates are unparseable or start > end.
    """
    getter = request_data.query_params if use_query_params else request_data.data
    start_str = getter.get("start_date")
    end_str = getter.get("end_date")

    if not start_str or not end_str:
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        return start_date, end_date

    try:
        start_date = timezone.datetime.fromisoformat(start_str)
        end_date = timezone.datetime.fromisoformat(end_str)
    except ValueError:
        raise ValueError("Invalid date format. Use ISO 8601 (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).")

    if timezone.is_naive(start_date):
        start_date = timezone.make_aware(start_date)
    if timezone.is_naive(end_date):
        end_date = timezone.make_aware(end_date)

    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    return start_date, end_date


def _serialize_signer(s):
    """
    Build the canonical signer dict from a Signer ORM instance.
    Resolves owner from RequesterEmail when present, falling back to userid.email.
    """
    owner = s.document.RequesterEmail if s.document.RequesterEmail else s.document.userid.email
    return {
        "uid": s.uid,
        "email": s.email,
        "signed": str(s.signed),
        "signers": s.document.signers,
        "created": s.document.docdate,
        "owner": owner,
        "docsigningcomplete": str(s.document.signedcomplete),
        "docvoided": str(s.document.declined),
        "signed_time_stamp": s.signed_timestamp,
        "current_signer": str(s.current_signer),
        "verify": str(s.isOtpVerify),
        "docname": s.document.title,
        "phone": s.phone,
        "guid": s.document.guid,
        "selfsign": str(s.document.selfsign),
        "assignmentd": s.document.assignmentd,
        "authenticate_signer": str(s.authenticate_signer) if s.authenticate_signer is not None else None,
    }


# ==============================================================================
# Authentication & Token Views
# ==============================================================================

@extend_schema(tags=["Authentication"])
class CentralizedLoginView(APIView):
    """
    Logs in a user via the centralized auth API and auto-creates them locally.
    Returns access and refresh tokens from central auth.
    """

    def post(self, request):
        serializer = CentralizedLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({
            "user_id": serializer.validated_data['user'].id,
            "access": serializer.validated_data['access'],
            "refresh": serializer.validated_data['refresh'],
        }, status=status.HTTP_200_OK)
@extend_schema(
    tags=["Authentication"],
    summary="Request a password reset email",
    request={"application/json": {"type": "object", "properties": {"email": {"type": "string"}}}},
    responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_view(request):
    """
    Send a password-reset link to the given email address.

    Generates a signed UID/token pair, renders a reset URL pointing at the
    frontend, and dispatches it via the configured SMTP service.
    """
    email = request.data.get("email")
    if not email:
        return create_error_response("Email is required")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return create_error_response("User with this email does not exist", status.HTTP_404_NOT_FOUND)

    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = f"{frontend_url}/reset/{uid}/{token}/"

    email_body = f"""
    <html>
    <body>
        <p>Dear {user.first_name},</p>
        <p>You have requested to reset your password for your Alignsys EDMS.</p>
        <p>Please click the link below to reset your password:</p>
        <p><a href="{reset_link}" style="color: blue; text-decoration: none;">Reset Password</a></p>
        <p>If you did not request this change, you can safely ignore this email.</p>
        <p>Best regards,<br>Alignsys Team</p>
    </body>
    </html>
    """

    result = send_email(email, email_body)
    if result["success"]:
        return create_success_response(
            "We've emailed you instructions for setting your password, if an account exists with "
            "the email you entered. You should receive them shortly. If you don't receive an email, "
            "please make sure you've entered the address you registered with, and check your spam folder."
        )
    return create_error_response(result["error"])


@extend_schema(
    tags=["Authentication"],
    summary="Confirm password reset using UID and token",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "uidb64": {"type": "string"},
                "token": {"type": "string"},
                "new_password": {"type": "string"},
            },
        }
    },
    responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """
    Validate the UID/token pair from a reset link and set the new password.

    All three fields — `uidb64`, `token`, and `new_password` — are required.
    Returns 400 if the token is invalid or expired.
    """
    uidb64 = request.data.get("uidb64")
    token = request.data.get("token")
    new_password = request.data.get("new_password")

    if not all([uidb64, token, new_password]):
        return create_error_response("Invalid data")

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.set_password(new_password)
        user.save()
        return create_success_response("Password reset was successful")

    return create_error_response("Invalid token")


@extend_schema(
    tags=["Authentication"],
    summary="Direct password reset (test/admin utility)",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "password": {"type": "string"},
            },
        }
    },
)
@api_view(["POST"])
def test_pass_reset(request):
    """
    Directly overwrite a user's password by email (no token required).

    **Warning:** This endpoint bypasses the normal reset flow. It should be
    restricted to admin/test environments and protected accordingly.
    """
    email = request.data["email"]
    password = request.data["password"]
    User.objects.filter(email=email).update(password=make_password(password))
    return JsonResponse({"msg": "Success"})


# ==============================================================================
# Company Views
# ==============================================================================

@extend_schema(
    tags=["Companies"],
    summary="Register a new company",
    responses={200: {"type": "object", "properties": {"response": {"type": "string"}, "name": {"type": "string"}}}},
)
@api_view(["POST"])
def register_company(request):
    """
    Submit a company registration request.

    On success, triggers a welcome email and generates an initial license (20 seats, tier 2).
    The company remains inactive until approved by a super-admin.
    """
    serializer = RegisterCompanySerializer(data=request.data)
    data = {}
    if serializer.is_valid():
        company = serializer.save()
        data["response"] = "Submitted successfully, approval to be confirmed within 24hrs"
        data["name"] = company.name
        send_email_newcompany(company.email, company.name)
        create_generate_license(company.id, 20, 2)
        return Response(data)
    return Response(serializer.errors, status=400)


@extend_schema(
    tags=["Companies"],
    summary="List all companies (super-admin)",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_companies_all_superadmin(request):
    """Return all registered companies regardless of approval status."""
    companies = Company.objects.all()
    response = [
        {
            "id": c.pk,
            "name": c.name,
            "email": c.email,
            "approved": str(c.approved),
            "active": str(c.active),
            "registered_date": str(c.registered_date),
        }
        for c in companies
    ]
    return JsonResponse(response, safe=False)


@extend_schema(
    tags=["Companies"],
    summary="List unapproved companies (super-admin)",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_companies_unapproved_superadmin(request):
    """Return companies that are pending approval."""
    companies = Company.objects.filter(approved=False)
    response = [
        {
            "id": c.pk,
            "name": c.name,
            "email": c.email,
            "approved": str(c.approved),
            "registered_date": str(c.registered_date),
        }
        for c in companies
    ]
    return JsonResponse(response, safe=False)


@extend_schema(
    tags=["Companies"],
    summary="List approved companies (super-admin)",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_companies_approved_superadmin(request):
    """Return all approved companies."""
    companies = Company.objects.filter(approved=True)
    response = [
        {
            "id": c.pk,
            "name": c.name,
            "email": c.email,
            "approved": str(c.approved),
            "active": str(c.active),
            "registered_date": str(c.registered_date),
        }
        for c in companies
    ]
    return JsonResponse(response, safe=False)


@extend_schema(
    tags=["Companies"],
    summary="Approve a company and create its admin account",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_company(request, id):
    """
    Approve a pending company registration.

    Generates a random password, creates an admin user for the company via
    `RegisterAdminSerializer`, marks the company as approved, and dispatches
    a welcome email with the new admin credentials.
    """
    pwd = generate_pdw()
    company_obj = Company.objects.get(pk=id)
    company_data = {
        "email": company_obj.email,
        "first_name": company_obj.name,
        "last_name": "Admin",
        "password1": pwd,
        "password2": pwd,
        "is_admin": True,
        "company": company_obj.pk,
    }
    serializer = RegisterAdminSerializer(data=company_data)
    if serializer.is_valid():
        user = serializer.save()
        Company.objects.filter(pk=id).update(approved=True)
        send_email_newadmin(company_obj, pwd)
        return Response(
            {"id": user.pk, "first": user.first_name, "last": user.last_name, "email": user.email}
        )
    return Response(serializer.errors, status=400)


@extend_schema(tags=["Companies"])
class CompanyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific company by primary key."""
    serializer_class = CompanySerializer
    queryset = Company.objects.all()


# ==============================================================================
# User Views
# ==============================================================================

@extend_schema(tags=["Users"])
class AddUserViewSet(viewsets.ModelViewSet):
    """ViewSet for creating users via the standard registration serializer."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


@extend_schema(
    tags=["Users"],
    summary="List users for a company",
    request={"application/json": {"type": "object", "properties": {"company": {"type": "integer"}}}},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_users(request):
    """
    Return all non-superuser members of the specified company.

    Expects `company` (company PK) in the request body.
    """
    users = User.objects.filter(company=request.data["company"], is_superuser=False)
    response = [
        {
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "phone": u.phone,
            "company": u.company.name,
            "is_active": str(u.is_active),
            "is_admin": str(u.is_admin),
        }
        for u in users
    ]
    return JsonResponse(response, safe=False)


@extend_schema(
    tags=["Users"],
    summary="List individual (non-corporate) users",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_Individual_Users(request):
    """Return all users belonging to the special 'individual@individual.com' company."""
    individual_company = Company.objects.get(email="individual@individual.com")
    users = User.objects.filter(company=individual_company)
    response = [
        {
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "phone": u.phone,
            "company": int(u.company.pk),
            "is_active": str(u.is_active),
        }
        for u in users
    ]
    return JsonResponse(response, safe=False)


@extend_schema(
    tags=["Users"],
    summary="List all company admins (super-admin view)",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_users_superadmin(request):
    """Return all admin users (excluding superusers), ordered by company."""
    users = User.objects.filter(is_admin=True, is_superuser=False).order_by("company")
    response = [
        {
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "phone": u.phone,
            "company": str(u.company),
            "is_active": str(u.is_active),
            "is_admin": str(u.is_admin),
        }
        for u in users
    ]
    return JsonResponse(response, safe=False)


@extend_schema(
    tags=["Users"],
    summary="Register a new user under a company admin",
)
@api_view(["POST"])
def register_user(request, adminid):
    """
    Create a new user scoped to the company of the given admin (`adminid`).

    Generates a random password, creates the user (idempotent via `get_or_create`),
    and dispatches login credentials via the Techedge mail service.
    Returns the new user's profile including the generated password.
    """
    try:
        company_admin = User.objects.get(pk=adminid)
        company = company_admin.company
    except User.DoesNotExist:
        return Response({"error": "Admin user not found"}, status=404)

    data = request.data
    email = data.get("email")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    phone = data.get("phone")

    if not all([email, first_name, last_name, phone]):
        return Response({"error": "All fields are required"}, status=400)

    pwd = generate_pdw()
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "company": company,
            "is_licensed": True,
        },
    )
    if created:
        user.set_password(pwd)
        user.save()

    api_url = "https://mailservice.techedge.dev/api/Email"
    email_body = f"""
    <html>
    <body>
        <p>Dear {user.first_name} {user.last_name},</p>
        <p>Your account has been successfully created for Techedge Corporate DSS.</p>
        <p>Your login details are as follows:</p>
        <p><b>Email:</b> {user.email}</p>
        <p><b>Password:</b> {pwd}</p>
        <p>Please log in and change your password after the first login.</p>
        <p>Best regards,<br>Alignsys Corporate DSS Team</p>
    </body>
    </html>
    """
    payload = {
        "Subject": (None, "Techedge Corporate DSS - Account Registration Completed"),
        "recipient": (None, user.email),
        "emailBody": (None, email_body),
        "ProfileID": (None, "40cdb363-0b1b-4bda-bfdc-a60cce499f11"),
        "cc": (None, ""),
        "bcc": (None, ""),
        "IsText": (None, "false"),
    }
    try:
        mail_response = requests.post(api_url, headers={"Accept": "*/*"}, files=payload)
        if mail_response.status_code != 201:
            logger.warning("Failed to send registration email. API response: %s", mail_response.text)
    except requests.exceptions.RequestException as e:
        logger.error("Email service error: %s", str(e))

    return Response(
        {
            "id": user.pk,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "password": pwd,
        },
        status=201,
    )


@extend_schema(
    tags=["Users"],
    summary="Register an individual (non-corporate) user",
)
@api_view(["POST"])
def register_individual_user(request):
    """
    Create a user under the 'individual' company.

    Returns 400 if the email already exists. On success, sends a welcome email
    with generated credentials and returns the new user's profile.
    """
    company = Company.objects.get(email="individual@individual.com")
    data = request.data
    email = data["email"]
    first_name = data["first_name"]
    last_name = data["last_name"]
    phone = data["phone"]

    try:
        User.objects.get(email=email)
        return Response(status=400)  # User already exists
    except ObjectDoesNotExist:
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            company=company,
        )
        pwd = generate_pdw()
        user.set_password(pwd)
        user.save()
        send_email_newuser(user, pwd)
        return Response(
            {
                "id": user.pk,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "password": pwd,
            },
            status=201,
        )


@extend_schema(
    tags=["Users"],
    summary="Bulk-import users from a CSV file",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_bulk_users(request):
    """
    Import users from an uploaded CSV file (`employeefile`).

    Expected CSV columns: `first_name`, `last_name`, `email`, `phone`.
    The `company` field in the request body sets the company FK for all rows.
    Uses `bulk_create` for efficiency; returns 500 on any DB error.
    """
    data = request.data
    companyid = data["company"]
    paramFile = io.TextIOWrapper(request.FILES["employeefile"].file)
    portfolio1 = csv.DictReader(paramFile)
    list_of_dict = list(portfolio1)
    objs = [
        User(
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"],
            phone=row["phone"],
            company=companyid,
        )
        for row in list_of_dict
    ]
    try:
        User.objects.bulk_create(objs)
        return JsonResponse({"status_code": 200})
    except Exception as e:
        logger.error("Error during bulk user import: %s", e)
        return JsonResponse({"status_code": 500})


@extend_schema(tags=["Users"])
class UserView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific user by primary key."""
    serializer_class = UserSerializer
    queryset = User.objects.all()


# ==============================================================================
# Avatar & Logo Views
# ==============================================================================

@extend_schema(tags=["Avatars & Logos"], summary="Get the current user's avatar URL")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getAvatar(request):
    """Return the avatar URL for the authenticated user."""
    serializer = UserAvatar(request.user)
    return Response(serializer.data)


@extend_schema(tags=["Avatars & Logos"], summary="Get the authenticated user's company logo URL")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getCompanyLogo(request):
    """Return the company logo for the authenticated user's organisation."""
    serializer = CompanyLogo(request.user.company)
    return Response(serializer.data)


@extend_schema(
    tags=["Avatars & Logos"],
    summary="Get a company logo by document GUID",
    request={"application/json": {"type": "object", "properties": {"docguid": {"type": "string"}}}},
)
@api_view(["POST"])
def getCompanyLogo2(request):
    """
    Resolve a company logo via the owning document's GUID.

    Returns a fully-qualified URL prefixed with `BASE_URL`. Returns 400 if
    the company has no custom logo (default placeholder detected) or if the
    document/user cannot be found.
    """
    guid = request.data["docguid"]
    doc = Document.objects.get(guid=guid)
    try:
        user = User.objects.get(id=doc.userid.pk)
        serializer = CompanyLogo(user.company)
        url = serializer.data["logo_url"]
        if url == "/media/Company/dafault.png":
            return Response({"msg": "Not found"}, status=400)
        return Response({"logo": f"{base_url}{url}"})
    except Exception:
        return Response({"msg": "Not found"}, status=400)


# ==============================================================================
# Document Upload Views
# ==============================================================================

@extend_schema(
    tags=["Document Uploads"],
    summary="Upload a single file for self-signing",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def uploadFile(request):
    """
    Forward a single uploaded file to the DSS SelfSign creation endpoint.

    Returns the `fileguid` (document GUID) assigned by the DSS service.
    """
    user_id = request.user.id
    files = [("formFile", request.FILES["formFile"])]
    url = f"{dss_api}/api/SelfSign/Create?uuid={user_id}"
    response = requests.request("POST", url, headers={}, data={}, files=files, verify=False)
    data = response.json()
    return Response({"fileguid": data["fileName"]})


@extend_schema(
    tags=["Document Uploads"],
    summary="Upload multiple ordered files for self-signing",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def uploadFileMultifile(request):
    """
    Upload multiple files for self-signing, preserving client-specified order.

    Files are re-ordered using the optional `fileIndex` POST list before being
    forwarded to the DSS SelfSign endpoint. Falls back to received order if
    index values are malformed.
    """
    user_id = request.user.id
    uploaded_files = request.FILES.getlist("formFile")
    indices = request.POST.getlist("fileIndex")

    if not uploaded_files:
        return Response({"error": "No files uploaded"}, status=400)

    try:
        paired = list(zip(map(int, indices), uploaded_files))
        ordered_files = [f for _, f in sorted(paired, key=lambda x: x[0])]
    except Exception as e:
        logger.warning("File ordering fallback triggered: %s", e)
        ordered_files = uploaded_files

    files = [
        ("formFile", (f.name, f, getattr(f, "content_type", "application/octet-stream")))
        for f in ordered_files
    ]
    payload = {"title": request.data.get("title", "")}
    url = f"{dss_api}/api/SelfSign/Create?uuid={user_id}"

    try:
        response = requests.post(url, files=files, data=payload, verify=False)
        if response.status_code == 200:
            data = response.json() if response.text else {}
            return Response({"fileguid": data.get("fileName", ""), "message": "Files uploaded successfully"})
        return Response(
            {"error": "External API upload failed", "status_code": response.status_code, "response": response.text},
            status=response.status_code,
        )
    except requests.RequestException as e:
        return Response({"error": f"Request failed: {str(e)}"}, status=500)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@extend_schema(
    tags=["Document Uploads"],
    summary="Upload a single file for multi-party signing",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def uploadFileothers(request):
    """
    Upload a document intended for signing by other parties.

    Forwards the file to the DSS `/api/Docs` endpoint along with the document
    title and the authenticated user's ID. Returns the DSS-assigned GUID and
    metadata on success.
    """
    user_id = request.user.id

    if "formFile" not in request.FILES or "title" not in request.data:
        return Response({"error": "Missing required file or title"}, status=400)

    files = {
        "formFile": (
            request.FILES["formFile"].name,
            request.FILES["formFile"],
            request.FILES["formFile"].content_type or "application/pdf",
        )
    }
    filename = request.data["title"]
    url = f"{dss_api}/api/Docs"
    payload = {
        "title": filename,
        "userid": str(user_id),
    }

    try:
        response = requests.post(url, headers={}, data=payload, files=files, verify=False)

        if response.status_code != 201:
            logger.warning("DSS upload failed for user %s: %s", user_id, response.text)
            return Response(
                {"error": "File upload failed", "details": response.text},
                status=response.status_code,
            )

        try:
            data = response.json()
            return Response({
                "fileguid": data.get("docGuid"),
                "title": data.get("title"),
                "docDate": data.get("docDate"),
                "signedTime": data.get("signedTime"),
                "userid": data.get("userid"),
            })
        except ValueError:
            return Response({"error": "Invalid JSON response from server"}, status=500)

    except requests.RequestException as e:
        return Response({"error": f"Request failed: {str(e)}"}, status=500)


@extend_schema(
    tags=["Document Uploads"],
    summary="Upload multiple files for multi-party signing",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def uploadFileothersMultifiles(request):
    """
    Upload multiple files at once for signing by other parties.

    Builds a multi-file payload and forwards it to the DSS `/api/Docs/CreateDocs`
    endpoint together with user identity and an optional `VaultGuid`.
    """
    user = request.user
    uploaded_files = request.FILES.getlist("formFile")

    if not uploaded_files:
        return Response({"error": "No files uploaded"}, status=400)

    files = [("formFile", (f.name, f, f.content_type)) for f in uploaded_files]
    data = {
        "userid": user.id,
        "IP": request.META.get("REMOTE_ADDR", ""),
        "title": request.data.get("title", ""),
        "VaultGuid": request.data.get("VaultGuid", ""),
        "email": user.email,
    }

    try:
        res = requests.post(f"{dss_api}/api/Docs/CreateDocs", data=data, files=files, verify=False)
        if res.status_code == 201:
            return Response(res.json(), status=201)
        return Response(
            {"error": "External API upload failed", "status_code": res.status_code, "response": res.text},
            status=res.status_code,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# ==============================================================================
# Document Views
# ==============================================================================

@extend_schema(
    tags=["Documents"],
    summary="Fetch a document by title from the DSS service",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def getDoc(request):
    """Proxy request to the DSS `/api/Doc/Getdocument/{doctitle}` endpoint."""
    doctitle = request.data["doctitle"]
    url = f"{dss_api}/api/Doc/Getdocument/{doctitle}"
    response = requests.request("GET", url, headers={}, data={}, verify=False)
    return JsonResponse(response.json(), safe=False)


@extend_schema(
    tags=["Documents"],
    summary="Get document signing status",
    request={"application/json": {"type": "object", "properties": {"guid": {"type": "string"}}}},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def docStatus(request):
    """
    Return the current signing status of a document.

    Response includes `complete`, `declined`, and a per-signer `signers` status
    list from the `signersStatus` model property.
    """
    guid = request.data.get("guid")
    try:
        doc = Document.objects.get(guid=guid)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=404)

    return Response({
        "complete": str(doc.signedcomplete),
        "declined": str(doc.declined),
        "signers": doc.signersStatus,
    })


@extend_schema(
    tags=["Documents"],
    summary="Get document signing status (admin, no auth required)",
)
@api_view(["POST"])
def docStatusAdmin(request):
    """
    Admin variant of `docStatus` — no authentication required.

    Intended for use by the DSS service or internal tooling that needs to
    check document state without a user JWT.
    """
    guid = request.data.get("guid")
    try:
        doc = Document.objects.get(guid=guid)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=404)

    return Response({
        "complete": str(doc.signedcomplete),
        "declined": str(doc.declined),
        "signers": doc.signersStatus,
    })


@extend_schema(
    tags=["Documents"],
    summary="Trash a document",
    request={
        "application/json": {
            "type": "object",
            "properties": {"signer_uid": {"type": "string"}, "docGuid": {"type": "string"}},
        }
    },
)
@api_view(["POST"])
def trash_document(request):
    """
    Mark a document as trashed via the DSS `/api/signers/TrashDocument` endpoint.

    Forwards both the signer UID and document GUID.
    """
    signer_uid = request.data["signer_uid"]
    guid = request.data["docGuid"]
    try:
        requests.post(
            f"{dss_api}/api/signers/TrashDocument",
            headers=_DSS_HEADERS,
            data=json.dumps({"signersGuid": signer_uid, "documentGuid": guid}),
            verify=False,
        )
        return Response({"msg": "trashed successfully"}, status=200)
    except Exception:
        return Response({"error": "Failed"}, status=400)


@extend_schema(
    tags=["Documents"],
    summary="Restore a trashed document",
)
@api_view(["POST"])
def untrash_document(request):
    """Restore a previously trashed document via DSS `/api/signers/UnTrashDocument`."""
    signer_uid = request.data["signer_uid"]
    guid = request.data["docGuid"]
    try:
        requests.post(
            f"{dss_api}/api/signers/UnTrashDocument",
            headers=_DSS_HEADERS,
            data=json.dumps({"signersGuid": signer_uid, "documentGuid": guid}),
            verify=False,
        )
        return Response({"msg": "untrashed successfully"}, status=200)
    except Exception:
        return Response({"error": "Failed"}, status=400)


@extend_schema(
    tags=["Documents"],
    summary="Resend document summary email",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_doc(request):
    """Trigger the DSS service to resend the document summary email to all parties."""
    file_guid = request.data.get("fileGuid")
    if not file_guid:
        return JsonResponse({"error": "fileGuid is required"}, status=400)
    try:
        response = requests.post(
            f"{dss_api}/api/Docs/ResendDoc",
            headers=_DSS_HEADERS,
            data=json.dumps({"fileGuid": file_guid}),
            verify=False,
        )
        return JsonResponse({"msg": "mailed successfully"}, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    tags=["Documents"],
    summary="Get document audit logs for the authenticated user's company",
    parameters=[
        OpenApiParameter("start_date", OpenApiTypes.DATETIME, description="ISO 8601 start date"),
        OpenApiParameter("end_date", OpenApiTypes.DATETIME, description="ISO 8601 end date"),
    ],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_doc_logs(request):
    """
    Return all documents belonging to the authenticated user's company within
    the given date range (defaults to the last 30 days).
    """
    user = request.user
    company_id = user.company.id

    try:
        start_date, end_date = _parse_date_range(request, use_query_params=True)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    try:
        docs = (
            Document.objects
            .filter(userid__company_id=company_id, docdate__range=(start_date, end_date))
            .select_related("userid")
        )
        documents = [
            {
                "guid": doc.guid,
                "title": doc.title,
                "owner": doc.userid.email if doc.userid else None,
                "docdate": doc.docdate,
                "signedcompletedate": doc.signeddate,
                "signers": doc.signers,
                "signedcomplete": str(doc.signedcomplete),
                "signeddate": doc.signeddate,
                "declined": str(doc.declined),
            }
            for doc in docs
        ]
        return JsonResponse(documents, safe=False)

    except Exception as e:
        logger.error("Error in get_doc_logs: %s", e, exc_info=True)
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)


@extend_schema(
    tags=["Documents"],
    summary="Get per-organisation document counts (excludes 'Individual')",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def getOrganizationDocCounts(request):
    """
    Aggregate document counts grouped by company name.

    Excludes documents owned by the special 'Individual' company. Results are
    sorted alphabetically.
    """
    try:
        queryset = (
            Document.objects
            .filter(trashed=False)
            .exclude(userid__company__name="Individual")
            .values("userid__company__name")
            .annotate(doc_count=Count("guid"))
            .order_by("userid__company__name")
        )
        response = [
            {"organization": org["userid__company__name"], "doc_count": org["doc_count"]}
            for org in queryset
        ]
        return JsonResponse(response, safe=False)
    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)


# ==============================================================================
# Inbox / Outbox / Uploads Mailbox Views
# ==============================================================================

@extend_schema(
    tags=["Mailbox"],
    summary="Get inbox (documents awaiting the current user's signature)",
    parameters=[
        OpenApiParameter("start_date", OpenApiTypes.DATETIME, description="ISO 8601 start date"),
        OpenApiParameter("end_date", OpenApiTypes.DATETIME, description="ISO 8601 end date"),
    ],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getInbox(request):
    """
    Return documents where the authenticated user is the current (active) signer.

    Filters by `document__docdate` within the supplied date range, defaulting
    to the last 30 days. Excludes trashed documents and trashed signer entries.
    """
    user_email = request.user.email

    try:
        start_date, end_date = _parse_date_range(request, use_query_params=True)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    try:
        queryset = (
            Signer.objects
            .filter(
                current_signer=True,
                email=user_email,
                trashed=False,
                document__trashed=False,
                document__docdate__range=(start_date, end_date),
            )
            .select_related("document", "document__userid")
            .order_by("document__docdate")
        )

        response = [
            {
                "uid": i.uid,
                "email": i.email,
                "signers": getattr(i.document, "signers", []),
                "title": i.document.title,
                "owner": i.document.userid.email if i.document.userid else None,
                "docdate": i.document.docdate,
                "guid": i.document.guid,
                "signedcomplete": str(i.document.signedcomplete),
                "declined": str(i.document.declined),
                "expirydate": i.document.expirydate,
                "selfsign": i.document.selfsign,
                "trashed": str(i.trashed),
            }
            for i in queryset
        ]
        return JsonResponse(response, safe=False)

    except Exception as e:
        logger.error("Error in getInbox: %s", e, exc_info=True)
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)


@extend_schema(
    tags=["Mailbox"],
    summary="Get outbox (sent documents pending completion)",
    parameters=[
        OpenApiParameter("start_date", OpenApiTypes.DATETIME, description="ISO 8601 start date"),
        OpenApiParameter("end_date", OpenApiTypes.DATETIME, description="ISO 8601 end date"),
    ],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getOutbox(request):
    """
    Return incomplete, non-voided documents where the user is owner or signer
    but NOT the current active signer.

    Skips documents with no signers. Defaults to the last 30 days.
    """
    user_email = request.user.email

    try:
        start_date, end_date = _parse_date_range(request, use_query_params=True)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    queryset = Document.objects.filter(
        signedcomplete=False,
        declined=False,
        trashed=False,
        docdate__range=(start_date, end_date),
    ).order_by("-docdate")

    documents = []
    for i in queryset:
        if len(i.signers) == 0:
            continue
        if (
            i.userid.email == user_email and user_email != i.getSignerCurrent
            or any(user_email == s and user_email != i.getSignerCurrent for s in i.signers_emails)
        ):
            documents.append({
                "guid": i.guid,
                "current_signer": i.getSignerCurrent,
                "title": i.title,
                "owner": i.userid.email,
                "docdate": i.docdate,
                "signers": i.signers,
                "signedcomplete": str(i.signedcomplete),
                "declined": str(i.declined),
                "expirydate": i.expirydate,
            })

    return JsonResponse(documents, safe=False)


@extend_schema(
    tags=["Mailbox"],
    summary="Get the authenticated user's uploaded documents (unsigned, unsent)",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getMyUploads(request):
    """
    Return documents uploaded by the user that have no signers assigned yet.

    These are draft documents that have not been sent for signing.
    """
    user = request.user
    queryset = Document.objects.filter(
        userid=user.id, signedcomplete=False, declined=False, trashed=False
    ).order_by("-docdate")

    documents = [
        {
            "guid": i.guid,
            "title": i.title,
            "owner": i.userid.email,
            "docdate": i.docdate,
            "signers": i.signers,
            "signedcomplete": str(i.signedcomplete),
            "declined": str(i.declined),
        }
        for i in queryset
        if not i.signers
    ]
    return JsonResponse(documents, safe=False)


@extend_schema(
    tags=["Mailbox"],
    summary="Get completed documents for the authenticated user",
    parameters=[
        OpenApiParameter("start_date", OpenApiTypes.DATETIME, description="ISO 8601 start date"),
        OpenApiParameter("end_date", OpenApiTypes.DATETIME, description="ISO 8601 end date"),
    ],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getComplete(request):
    """
    Return fully-signed documents where the user is the owner, a signer,
    or listed in `OtherSignersTable`.

    Signer lookups are pre-fetched as sets to avoid per-document queries.
    Defaults to the last 30 days.
    """
    user = request.user

    try:
        start_date, end_date = _parse_date_range(request, use_query_params=True)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    try:
        base_queryset = Document.objects.filter(
            signedcomplete=True,
            declined=False,
            trashed=False,
            docdate__range=(start_date, end_date),
        ).order_by("-docdate")

        signer_doc_guids = set(
            Signer.objects.filter(email=user.email).values_list("document__guid", flat=True)
        )
        other_signer_doc_guids = set(
            OtherSignersTable.objects.filter(Email=user.email).values_list("fileguid", flat=True)
        )

        documents = []
        for doc in base_queryset:
            is_owner = doc.userid and user.email == doc.userid.email
            is_signer = doc.guid in signer_doc_guids
            is_other_signer = doc.guid in other_signer_doc_guids

            if is_owner or is_signer or is_other_signer:
                documents.append({
                    "guid": doc.guid,
                    "title": doc.title,
                    "owner": doc.userid.email if doc.userid else None,
                    "docdate": doc.docdate,
                    "signers": doc.signers if doc.signers else None,
                    "signedcomplete": str(doc.signedcomplete),
                    "signeddate": doc.signeddate,
                    "declined": str(doc.declined),
                })

        return JsonResponse(documents, safe=False)

    except Exception as e:
        logger.error("Error in getComplete: %s", e, exc_info=True)
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)


@extend_schema(
    tags=["Mailbox"],
    summary="Get completed documents for the authenticated user (admin view, by email)",
)
@api_view(["POST"])
def getComplete_admin(request):
    """
    Admin variant of `getComplete` — accepts `email` in the request body instead
    of deriving it from the JWT. No authentication decorator applied; protect
    at the network / gateway level as appropriate.
    """
    user_email = request.data["email"]
    queryset = Document.objects.filter(signedcomplete=True, declined=False, trashed=False).order_by("-docdate")
    documents = []
    for document in queryset:
        doc_data = {
            "guid": document.guid,
            "title": document.title,
            "owner": document.userid.email if document.userid else None,
            "docdate": document.docdate if document.docdate else None,
            "signedcomplete": str(document.signedcomplete),
            "signeddate": document.signeddate if document.signeddate else None,
            "declined": str(document.declined),
        }
        if user_email in document.signers_emails or user_email == document.RequesterEmail:
            documents.append(doc_data)
    return JsonResponse(documents, safe=False)


@extend_schema(tags=["Mailbox"], summary="Get voided documents for the authenticated user")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getVoided(request):
    """Return declined (voided) documents where the user appears as a signer."""
    user = request.user
    queryset = Document.objects.filter(declined=True, trashed=False).order_by("-docdate")
    documents = [
        {
            "guid": i.guid,
            "title": i.title,
            "owner": i.userid.email,
            "docdate": i.docdate,
            "signers": i.signers,
            "signedcomplete": str(i.signedcomplete),
            "signeddate": i.signeddate,
            "declined": str(i.declined),
        }
        for i in queryset
        if user.email in i.signers_emails
    ]
    return JsonResponse(documents, safe=False)


@extend_schema(tags=["Mailbox"], summary="Get trashed documents for the authenticated user")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getTrashed(request):
    """Return the user's trashed signer entries and their associated document metadata."""
    user = request.user
    queryset = (
        Signer.objects
        .filter(email=user.email, trashed=True, document__declined=False)
        .select_related("document")
        .order_by("document__docdate")
    )
    response = [
        {
            "uid": i.uid,
            "email": i.email,
            "signers": i.document.signers,
            "title": i.document.title,
            "owner": i.document.userid.email,
            "docdate": i.document.docdate,
            "guid": i.document.guid,
            "signedcomplete": str(i.document.signedcomplete),
            "declined": str(i.document.declined),
            "expirydate": i.document.expirydate,
            "selfsign": i.document.selfsign,
        }
        for i in queryset
    ]
    return JsonResponse(response, safe=False)


# ==============================================================================
# Signing & Signer Views
# ==============================================================================

@extend_schema(
    tags=["Signing"],
    summary="Get signer details by signer UID",
    request={"application/json": {"type": "object", "properties": {"uid": {"type": "string"}}}},
)
@api_view(["POST"])
def getSigner(request):
    """
    Return a full signer profile for the given `uid`.

    Consolidates the four branching cases (OTP-verified × RequesterEmail present)
    into a single helper (`_serialize_signer`) since the payload is identical
    across all branches.
    """
    uid = request.data["uid"]
    s = Signer.objects.get(uid=uid)
    return JsonResponse(_serialize_signer(s), safe=False)


@extend_schema(
    tags=["Signing"],
    summary="Get the authenticated user's signer record for a document",
    request={"application/json": {"type": "object", "properties": {"docguid": {"type": "string"}}}},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def getSigner2(request):
    """
    Retrieve a signer record by document GUID for the currently authenticated user.

    Returns 400 if no matching signer is found.
    """
    user = request.user
    guid = request.data["docguid"]
    signer = Signer.objects.get(document=guid, email=user.email)

    if signer:
        return Response({
            "uid": signer.uid,
            "docguid": signer.document.guid,
            "signers": signer.document.signers,
            "docname": signer.document.title,
            "created": signer.document.docdate,
            "owner": signer.document.userid.email,
            "assignmentd": signer.document.assignmentd,
        }, status=200)
    return Response({"uid": "no signer found with search details"}, status=400)


@extend_schema(
    tags=["Signing"],
    summary="Get the current active signer for a document",
    request={"application/json": {"type": "object", "properties": {"guid": {"type": "string"}}}},
)
@api_view(["POST"])
def getCurrentSigner(request):
    """Return the UID of the signer whose `current_signer` flag is True for the given document."""
    guid = request.data["guid"]
    doc = Document.objects.get(guid=guid)
    s = Signer.objects.get(document=doc, current_signer=True)
    return JsonResponse({"uid": s.uid}, safe=False)


@extend_schema(
    tags=["Signing"],
    summary="Get saved signatures for an email address",
    request={"application/json": {"type": "object", "properties": {"email": {"type": "string"}}}},
)
@api_view(["POST"])
def getSavedSignatures(request):
    """Proxy to the DSS `/api/SaveSignature/Receive` endpoint for fetching stored signatures."""
    email = request.data["email"]
    url = f"{dss_api}/api/SaveSignature/Receive?Email={email}"
    response = requests.request("POST", url, headers={}, data={}, verify=False)
    return JsonResponse(response.json(), safe=False)


@extend_schema(
    tags=["Signing"],
    summary="Close a self-signed document",
    request={"application/json": {"type": "object", "properties": {"fileGuid": {"type": "string"}}}},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def selfSignCloseSigning(request):
    """Signal the DSS service that a self-signing session is complete."""
    file_guid = request.data["fileGuid"]
    payload = json.dumps({"fileGuid": file_guid})
    response = requests.request(
        "POST", f"{dss_api}/api/SelfSign/CloseDocumentSigning",
        headers=_DSS_HEADERS, data=payload, verify=False,
    )
    return JsonResponse(response.json(), safe=False)


@extend_schema(
    tags=["Signing"],
    summary="Add a saved signature to a self-sign document",
    request={
        "application/json": {
            "type": "object",
            "properties": {"documentid": {"type": "string"}},
        }
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def selfSignSaved(request):
    """
    Apply a previously saved signature to a document.

    Steps:
    1. Untrash the document via DSS `/api/Doc/UnTrash`.
    2. Add the authenticated user as a self-signer via DSS `/api/SelfSign/AddSelfSign`.
    """
    user = request.user
    documentid = request.data.get("documentid")

    if not documentid:
        return Response({"msg": "Missing documentid"}, status=400)

    headers = _DSS_HEADERS

    # Step 1 — untrash
    resp_untrash = requests.post(
        f"{dss_api}/api/Doc/UnTrash",
        headers=headers,
        data=json.dumps({"docGuid": documentid}),
        verify=False,
    )
    if resp_untrash.status_code != 200:
        return Response({"msg": "Failed to untrash document"}, status=400)

    # Step 2 — add self-sign
    resp_sign = requests.post(
        f"{dss_api}/api/SelfSign/AddSelfSign",
        headers=headers,
        data=json.dumps({"documentid": documentid, "signers": [{"email": user.email}]}),
        verify=False,
    )
    if resp_sign.status_code != 200:
        return Response({"msg": "Failed to add self-signature"}, status=400)

    return Response(resp_sign.json(), status=200)


@extend_schema(
    tags=["Signing"],
    summary="Submit signers and annotations for a document",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def otherSigners(request):
    """
    Assign signers to a document and optionally store per-signer annotations.

    Required fields: `signers` (list), `documentid` (string).
    Optional fields: `annotations`, `assignmentd`, `originatorname`, `originatoremail`.

    Forwards the signer list to DSS, then persists any `SignerAnnotation` objects
    for the newly created signer records.
    """
    data = request.data

    if not data or "signers" not in data or "documentid" not in data:
        return Response({"error": "Missing required fields in the data."}, status=status.HTTP_400_BAD_REQUEST)

    signers = data["signers"]
    annotations = data.get("annotations", [])
    documentid = data["documentid"]

    # Optional document metadata updates
    update_fields = {}
    if "assignmentd" in data:
        update_fields["assignmentd"] = data["assignmentd"]
    if "originatorname" in data:
        update_fields["RequesterName"] = data["originatorname"]
    if "originatoremail" in data:
        update_fields["RequesterEmail"] = data["originatoremail"]
    if update_fields:
        Document.objects.filter(guid=documentid).update(**update_fields)

    payload = json.dumps({"documentid": documentid, "signers": signers})
    response = requests.post(f"{dss_api}/api/signers", data=payload, headers=_DSS_HEADERS, verify=False)

    if annotations:
        document = Document.objects.filter(guid=documentid).first()
        if not document:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        for signer_data in signers:
            signer_email = signer_data["email"]
            try:
                signer = Signer.objects.get(email=signer_email, document=document)
            except Signer.DoesNotExist:
                return Response(
                    {"error": f"Signer with email {signer_email} not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            for annotation_data in annotations:
                if annotation_data["signer"]["email"] == signer_email:
                    for annotation_info in annotation_data["annotations"]:
                        SignerAnnotation.objects.create(
                            signer=signer,
                            id=float(annotation_info["id"]),
                            page_number=annotation_info["pageNumber"],
                            x=annotation_info["x"],
                            y=annotation_info["y"],
                            width=annotation_info["width"],
                            height=annotation_info["height"],
                            text=annotation_info.get("text", ""),
                            color=annotation_info.get("color", ""),
                        )

    return Response(response.json(), status=status.HTTP_200_OK)


@extend_schema(
    tags=["Signing"],
    summary="Re-add signers to an already-signed document",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def otherSignersOnceSigned(request):
    """
    Append additional signers to a document that already has signatures.

    Optionally updates the `assignmentd` field before forwarding the signer
    list to the DSS `/api/signers` endpoint.
    """
    data = request.data
    signers = data["signers"]
    documentid = data["documentid"]

    if "assignmentd" in data:
        Document.objects.filter(guid=documentid).update(assignmentd=data["assignmentd"])

    payload = json.dumps({"documentid": documentid, "signers": signers})
    response = requests.request("POST", f"{dss_api}/api/signers", data=payload, headers=_DSS_HEADERS, verify=False)
    return Response(response)


@extend_schema(
    tags=["Signing"],
    summary="Void a document as the owner",
    request={"application/json": {"type": "object", "properties": {"guid": {"type": "string"}}}},
)
@api_view(["POST"])
def ownerVoid(request):
    """
    Void (decline) a document on behalf of its owner.

    Calls the DSS `/api/SendSigning/OwnerDecline` endpoint.
    """
    guid = request.data["guid"]
    payload = json.dumps({"fileGuid": f"{guid}"})
    response = requests.request(
        "POST", f"{dss_api}/api/SendSigning/OwnerDecline",
        headers=_DSS_HEADERS, data=payload, verify=False,
    )
    if response.status_code == 200:
        return Response({"msg": "Voided"}, status=200)
    return Response({"msg": "something went wrong"}, status=400)


@extend_schema(
    tags=["Signing"],
    summary="Void a document (authenticated owner endpoint)",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def owner_voiding(request):
    """
    Authenticated variant of `ownerVoid`. Requires `fileGuid` in the request body.
    Returns 400 if the field is absent; propagates the DSS response status code.
    """
    file_guid = request.data.get("fileGuid")
    if not file_guid:
        return JsonResponse({"error": "fileGuid is required"}, status=400)

    payload = json.dumps({"fileGuid": file_guid})
    try:
        response = requests.post(
            f"{dss_api}/api/SendSigning/OwnerDecline",
            headers=_DSS_HEADERS,
            data=payload,
            verify=False,
        )
        return JsonResponse({"msg": "voided successfully"}, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    tags=["Signing"],
    summary="Resend signing email to a specific signer",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_to_signer(request):
    """Trigger the DSS service to resend the signing invitation to the current signer."""
    file_guid = request.data.get("fileGuid")
    if not file_guid:
        return JsonResponse({"error": "fileGuid is required"}, status=400)
    try:
        response = requests.post(
            f"{dss_api}/api/signers/Resend",
            headers=_DSS_HEADERS,
            data=json.dumps({"fileGuid": file_guid}),
            verify=False,
        )
        return JsonResponse({"msg": "mailed successfully"}, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


# ==============================================================================
# Comments & Annotations Views
# ==============================================================================

@extend_schema(
    tags=["Comments & Annotations"],
    summary="Get all comments for a document",
    request={"application/json": {"type": "object", "properties": {"guid": {"type": "string"}}}},
)
@api_view(["POST"])
def getComments(request):
    """Retrieve all comments left by any signer on the given document (identified by GUID)."""
    guid = request.data["guid"]
    signers = Signer.objects.filter(document=guid)
    commentslist = []
    for signer in signers:
        for c in signer.getSignersComments:
            commentslist.append({
                "owner": c.signer.email,
                "comment": c.comment,
                "created": c.posted,
                "docguid": c.signer.document.guid,
            })
    return JsonResponse(commentslist, safe=False)


@extend_schema(
    tags=["Comments & Annotations"],
    summary="Add a comment for a signer",
    request={
        "application/json": {
            "type": "object",
            "properties": {"signer": {"type": "string"}, "comment": {"type": "string"}},
        }
    },
)
@api_view(["POST"])
def addComment(request):
    """
    Create a new comment for the signer identified by `signer` (UID).

    Uses `get_or_create` — returns 400 if the identical comment already exists.
    """
    signer_guid = request.data["signer"]
    comment_text = request.data["comment"]
    get_signer = Signer.objects.get(uid=signer_guid)
    _, created = Comment.objects.get_or_create(comment=comment_text, signer=get_signer)
    return Response({"created": created}, status=200 if created else 400)


@extend_schema(
    tags=["Comments & Annotations"],
    summary="Apply an image annotation (signature stamp) to a document page",
)
@api_view(["POST"])
def annotate(request):
    """
    Render a signature annotation onto a document page using `annotate_image` from tasks.

    Returns the annotated image as a base64-encoded string in the `signature` field.
    """
    try:
        annotated_image_base64 = annotate_image(request.data)
        return Response({"signature": annotated_image_base64}, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": "An error occurred: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["Comments & Annotations"],
    summary="Get annotations for a signer on a specific document",
    request={
        "application/json": {
            "type": "object",
            "properties": {"email": {"type": "string"}, "documentId": {"type": "string"}},
        }
    },
)
@api_view(["POST"])
def get_annotations_by_signer_email_and_document(request):
    """
    Return all `SignerAnnotation` records for the signer matched by email
    and document GUID.

    Returns 404 if either the document or the signer cannot be found.
    """
    email = request.data.get("email")
    document_id = request.data.get("documentId")

    if not email or not document_id:
        return Response({"detail": "Email and documentId are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        document = Document.objects.get(guid=document_id)
    except Document.DoesNotExist:
        return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

    signer = Signer.objects.filter(document=document, email=email).first()
    if not signer:
        return Response(
            {"detail": "Signer not found for the provided email and document"},
            status=status.HTTP_404_NOT_FOUND,
        )

    annotations = SignerAnnotation.objects.filter(signer=signer)
    annotations_data = [
        {
            "annotation_id": a.id,
            "page_number": a.page_number,
            "x": a.x,
            "y": a.y,
            "width": a.width,
            "height": a.height,
            "text": a.text,
            "color": a.color,
        }
        for a in annotations
    ]
    return Response(annotations_data, status=status.HTTP_200_OK)


# ==============================================================================
# Workflow Views
# ==============================================================================

@extend_schema(tags=["Workflows"], summary="List the authenticated user's personal workflows")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getWorkflows(request):
    """Return all workflows owned by the authenticated user."""
    wfs = Workflow.objects.filter(owner=request.user)
    return Response([
        {"id": wf.id, "title": wf.title, "owner": wf.owner.email, "signers": wf.workflowusers_emails}
        for wf in wfs
    ])


@extend_schema(
    tags=["Workflows"],
    summary="Create a new personal workflow",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "wftitle": {"type": "string"},
                "wfsigners": {"type": "array", "items": {"type": "object"}},
            },
        }
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def saveWorflow(request):
    """
    Create a workflow with the given title and signer list.

    Each signer entry must contain `email`; providing `phone` additionally
    marks the signer for OTP verification.
    """
    data = request.data
    wf = Workflow.objects.create(title=data["wftitle"], owner=request.user)

    for signer in data["wfsigners"]:
        if "phone" in signer:
            WorkflowUser.objects.create(
                email=signer["email"], phone=signer["phone"], otpverification=True, workflow=wf
            )
        else:
            WorkflowUser.objects.create(email=signer["email"], workflow=wf)

    result = Workflow.objects.get(id=wf.id)
    return Response({"id": result.id, "title": result.title, "signers": result.workflowusers_emails})


@extend_schema(tags=["Workflows"], summary="Delete a personal workflow")
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def deleteWorkflow(request, workflow_id):
    """
    Delete the workflow identified by `workflow_id`.

    Only the owning user may delete their workflow; returns 404 otherwise.
    """
    try:
        workflow = Workflow.objects.get(pk=workflow_id, owner=request.user)
        workflow.delete()
        return Response({"message": "Workflow deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    except Workflow.DoesNotExist:
        return Response({"error": "Workflow not found or unauthorized access."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=["Workflows"], summary="List organisation-level workflows")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getOrganizationWorkflows(request):
    """Return all workflows owned by the authenticated user's organisation."""
    organization = Company.objects.get(id=request.user.company.id)
    wfs = OrganizationWorkflow.objects.filter(owner=organization)
    return Response([
        {"id": wf.id, "title": wf.title, "owner": wf.owner.email, "signers": wf.workflowusers_emails}
        for wf in wfs
    ])


@extend_schema(tags=["Workflows"], summary="Create an organisation-level workflow")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def createOrganizationWorkflow(request):
    """
    Create a new workflow scoped to the authenticated user's organisation.

    Requires `title`; `users` (list of objects with `email`) is optional.
    """
    user = request.user
    try:
        organization = Company.objects.get(id=user.company.id)
    except Company.DoesNotExist:
        return Response({"detail": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)

    title = request.data.get("title")
    users = request.data.get("users", [])

    if not title:
        return Response({"detail": "Title is required."}, status=status.HTTP_400_BAD_REQUEST)

    workflow = OrganizationWorkflow.objects.create(title=title, owner=organization)

    for user_data in users:
        email = user_data.get("email")
        if email:
            OrganizationWorkflowUser.objects.create(
                workflow=workflow, fullname="", email=email, phone="", otpverification=False
            )

    return Response({
        "id": workflow.id,
        "title": workflow.title,
        "owner": workflow.owner.email,
        "signers": workflow.workflowusers_emails,
    }, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Workflows"], summary="Update an organisation-level workflow")
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def updateOrganizationWorkflow(request, workflow_id):
    """
    Update the title and/or member list of an organisation workflow.

    Members not present in the new `users` list are removed; existing members
    are updated in-place; new members are created.
    """
    user = request.user
    try:
        organization = Company.objects.get(id=user.company.id)
    except Company.DoesNotExist:
        return Response({"detail": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        workflow = OrganizationWorkflow.objects.get(id=workflow_id, owner=organization)
    except OrganizationWorkflow.DoesNotExist:
        return Response({"detail": "Workflow not found."}, status=status.HTTP_404_NOT_FOUND)

    title = request.data.get("title")
    users = request.data.get("users", [])

    if title is not None:
        workflow.title = title
        workflow.save()

    existing_users = OrganizationWorkflowUser.objects.filter(workflow=workflow)
    existing_emails = set(existing_users.values_list("email", flat=True))
    incoming_emails = set(u.get("email") for u in users if u.get("email"))

    # Remove users no longer in the list
    OrganizationWorkflowUser.objects.filter(
        workflow=workflow, email__in=existing_emails - incoming_emails
    ).delete()

    # Create or update remaining users
    for user_data in users:
        email = user_data.get("email")
        if not email:
            continue
        user_entry, created = OrganizationWorkflowUser.objects.get_or_create(
            workflow=workflow,
            email=email,
            defaults={
                "fullname": user_data.get("fullname", ""),
                "phone": user_data.get("phone", ""),
                "otpverification": user_data.get("otpverification", False),
            },
        )
        if not created:
            user_entry.fullname = user_data.get("fullname", user_entry.fullname)
            user_entry.phone = user_data.get("phone", user_entry.phone)
            user_entry.otpverification = user_data.get("otpverification", user_entry.otpverification)
            user_entry.save()

    updated_signers = OrganizationWorkflowUser.objects.filter(workflow=workflow).values(
        "id", "fullname", "email", "phone", "otpverification"
    )
    return Response({
        "id": workflow.id,
        "title": workflow.title,
        "owner": workflow.owner.email,
        "signers": list(updated_signers),
    })


@extend_schema(tags=["Workflows"], summary="Delete an organisation-level workflow")
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def deleteOrganizationWorkflow(request, workflow_id):
    """Delete an organisation workflow. Only accessible by members of the owning organisation."""
    user = request.user
    try:
        organization = Company.objects.get(id=user.company.id)
    except Company.DoesNotExist:
        return Response({"detail": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        workflow = OrganizationWorkflow.objects.get(id=workflow_id, owner=organization)
    except OrganizationWorkflow.DoesNotExist:
        return Response({"detail": "Workflow not found."}, status=status.HTTP_404_NOT_FOUND)

    workflow.delete()
    return Response({"detail": "Workflow deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


# ==============================================================================
# Logs & Activity Views
# ==============================================================================

@extend_schema(
    tags=["Logs & Activity"],
    summary="Query user activity logs",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
        }
    },
)
@api_view(["POST"])
def user_activity(request):
    """
    Return activity log entries filtered by email domain substring and date range.

    `domain` is matched case-insensitively against the `user` field of each
    `Logger` record. Defaults to the last 30 days when no date range is provided.
    """
    domain = request.data.get("domain", "")

    try:
        start_date, end_date = _parse_date_range(request)
    except ValueError as e:
        return Response({"error": str(e)}, status=400)

    try:
        activities = (
            Logger.objects
            .filter(user__icontains=domain, created_date__range=(start_date, end_date))
            .order_by("-created_date")
        )

        response_data = []
        for i in activities:
            entry = {
                "id": i.id,
                "description": i.description,
                "created": humanize_timestamp(f"{i.created_date}"),
            }
            if i.getotpphone:
                entry["otpnumber"] = i.getotpphone
            if i.activity:
                entry["activity"] = i.activity
            if i.ip:
                entry["ip"] = i.ip
            if i.guid:
                entry["guid"] = i.guid
            if i.user:
                entry["user"] = i.user
            response_data.append(entry)

        return Response(response_data, status=200)

    except Exception as e:
        logger.error("Error in user_activity: %s", e, exc_info=True)
        return Response({"error": "An unexpected error occurred."}, status=500)


@extend_schema(
    tags=["Logs & Activity"],
    summary="Create a new activity log entry",
)
@api_view(["POST"])
def log_user_activity(request):
    """
    Persist a new `Logger` record.

    Expected fields: `user`, `activity`, `description`, `ip`, `guid`.
    """
    try:
        Logger.objects.create(
            ip=request.data["ip"],
            activity=request.data["activity"],
            user=request.data["user"],
            description=request.data["description"],
            guid=request.data["guid"],
        )
        return Response({"msg": "logged successfully", "status": 200}, status=200)
    except Exception:
        return Response({"msg": "something went wrong", "status": 400}, status=400)


# ==============================================================================
# Settings & SMTP Config Views
# ==============================================================================

@extend_schema(
    tags=["Settings & Config"],
    summary="Create or update SMTP configuration for the current user's company",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_or_create_smtp_config(request):
    """
    Upsert the SMTP configuration for the authenticated user's company.

    Performs a partial update if a config already exists; otherwise creates
    a new one. The `user` field is automatically set to the authenticated user.
    """
    user = User.objects.get(pk=request.user.pk)
    try:
        smtp_config = SMTPConfigs.objects.get(user__company=user.company)
        serializer = SMTPConfigsSerializer(smtp_config, data=request.data, partial=True)
    except SMTPConfigs.DoesNotExist:
        serializer = SMTPConfigsSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(user=user)
        return Response(serializer.data, status=200)
    return Response(serializer.errors, status=400)


@extend_schema(tags=["Settings & Config"], summary="Retrieve SMTP configuration for the current user's company")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_smtp_config(request):
    """Return the SMTP settings for the authenticated user's company."""
    user = User.objects.get(pk=request.user.pk)
    try:
        smtp_config = SMTPConfigs.objects.get(user__company=user.company)
        return Response({
            "url": smtp_config.url,
            "username": smtp_config.username,
            "port": smtp_config.port,
            "display_name": smtp_config.display_name,
            "password": smtp_config.password,
        }, status=200)
    except SMTPConfigs.DoesNotExist:
        return Response({"error": "not found"}, status=400)


@extend_schema(tags=["Settings & Config"], summary="Get the client's IP address")
@api_view(["GET"])
def get_client_ip(request):
    """
    Return the originating IP address of the request.

    Honours the `X-Forwarded-For` header when the service is behind a proxy.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")
    return JsonResponse({"ip": ip}, safe=False)


# ==============================================================================
# OTP Views
# ==============================================================================

@extend_schema(
    tags=["OTP"],
    summary="Send an OTP to a phone number",
    request={"application/json": {"type": "object", "properties": {"phone": {"type": "string"}}}},
)
@api_view(["POST"])
def send_otp(request):
    """
    Dispatch a one-time password to the provided phone number via the OTP service.

    Returns 200 with `status: 200` on success; 400 on failure.
    """
    phone = request.data["phone"]
    try:
        result = sendOTP(phone)
        if result == "pending":
            return Response({"status": 200, "msg": "sent successfully", "recepient": phone})
        return Response({"status": 400, "msg": "something went wrong"})
    except Exception:
        return Response({"status": 400, "msg": "something went wrong"})


@extend_schema(
    tags=["OTP"],
    summary="Verify an OTP against a phone number",
    request={
        "application/json": {
            "type": "object",
            "properties": {"otp": {"type": "string"}, "phone": {"type": "string"}},
        }
    },
)
@api_view(["POST"])
def verify_otp(request):
    """
    Verify an OTP code for the given phone number.

    Returns:
    - 200 `approved` — OTP matched.
    - 400 `pending` — OTP not yet approved.
    - 500 `expired` — OTP expired; user should request a new one.
    """
    otp = request.data["otp"]
    phone = request.data["phone"]
    result = verifyOTP(phone, otp)

    if result == "approved":
        return Response({"status": 200, "msg": "approved successfully", "recepient": phone})
    elif result == "pending":
        return Response({"status": 400, "msg": "verification failed"})
    return Response({"status": 500, "msg": "verification failed, otp expired, try again later"})


# ==============================================================================
# File Serving Views
# ==============================================================================

@extend_schema(tags=["Files"], summary="Retrieve a PDF file as a base64 data URI")
class PDFFileView(APIView):
    """
    Return the requested PDF file from `BASE_FILE_DIR` as a base64-encoded
    data URI suitable for embedding directly in a browser.

    The `file` path parameter is the filename (not a full path). Raises a
    standard Python `FileNotFoundError` if the file does not exist.
    """

    def get(self, request, file):
        pdf_path = os.path.join(settings.BASE_FILE_DIR, file)
        with open(pdf_path, "rb") as f:
            pdf_content = base64.b64encode(f.read()).decode("utf-8")
        return Response({"base64_uri": f"data:application/pdf;base64,{pdf_content}"})


# ==============================================================================
# Admin-Only / Internal Views (no auth — protect at network level)
# ==============================================================================

@extend_schema(
    tags=["Admin"],
    summary="Get outbox documents by email (admin, no auth)",
)
@api_view(["POST"])
def getOutbox_admin(request):
    """
    Admin variant of `getOutbox` that accepts `email` in the request body
    rather than reading from the JWT.

    No authentication decorator applied — this endpoint should be protected at
    the infrastructure/gateway level.
    """
    user_email = request.data["email"]
    queryset = Document.objects.filter(signedcomplete=False, declined=False, trashed=False).order_by("-docdate")
    documents = []
    for i in queryset:
        if (
            i.userid.email == user_email and user_email != i.getSignerCurrent
            or any(user_email == s and user_email != i.getSignerCurrent for s in i.signers_emails)
        ):
            documents.append({
                "guid": i.guid,
                "current_signer": i.getSignerCurrent,
                "title": i.title,
                "owner": i.userid.email,
                "docdate": i.docdate,
                "signers": i.signers,
                "signedcomplete": str(i.signedcomplete),
                "declined": str(i.declined),
            })
    return JsonResponse(documents, safe=False)


@extend_schema(
    tags=["Admin"],
    summary="Get inbox documents by email (admin, no auth)",
)
@api_view(["POST"])
def getIbox_admin(request):
    """
    Admin variant of `getInbox` — resolves the user from the request body `email`.

    No authentication decorator applied — this endpoint should be protected at
    the infrastructure/gateway level.
    """
    user_email = request.data["email"]
    queryset = (
        Signer.objects
        .filter(current_signer=True, email=user_email, document__trashed=False)
        .select_related("document__userid")
        .order_by("document__docdate")
    )
    response = [
        {
            "uid": i.uid,
            "email": i.email,
            "signers": i.document.signers if i.document.signers is not None else None,
            "title": i.document.title if i.document.title is not None else None,
            "owner": i.document.userid.email if i.document.userid and i.document.userid.email is not None else None,
            "docdate": i.document.docdate if i.document.docdate else None,
            "guid": i.document.guid if i.document.guid is not None else None,
            "signedcomplete": str(i.document.signedcomplete) if i.document.signedcomplete is not None else None,
            "declined": str(i.document.declined) if i.document.declined is not None else None,
        }
        for i in queryset
    ]
    return JsonResponse(response, safe=False)