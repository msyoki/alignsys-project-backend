import csv
import re
import logging
from io import StringIO

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
import secrets
import string

from .utils import generate_password


from .mailer import send_email
from .models import (
    EventLog,
    LoginLog,
    Organization,
    UserGroup,
    UserVaultID,
    Vault,
    EDMSUser,
)
from .serializers import (
    EventLogSerializer,
    EDMSUserSerializer,
    OrganizationSerializer,
)
from .auth.serializers.external_auth_serializer import ExternalAuthTokenSerializer
from .auth.serializers.internal_auth_serializer import (
    InternalOrDomainAuthTokenSerializer,
)


# Constants
DEFAULT_PASSWORD = generate_password()
ALL_INTERNAL_USERS_GROUP = "All Internal Users"
DOMAIN_VAULT_ROLE_ADMIN = "3079"
DEFAULT_LIMIT = 100

# Settings
base_url = settings.BACKEND_API
server_ip = settings.SERVER_IP
mail_service_url = settings.MAIL_SERVICE_API

# Set up logging
logger = logging.getLogger(__name__)
User = get_user_model()


def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))


# Helper Functions
def create_error_response(
    message, status_code=status.HTTP_400_BAD_REQUEST, extra_data=None
):
    """Create standardized error response"""
    data = {"error": message}
    if extra_data:
        data.update(extra_data)
    return Response(data, status=status_code)


def create_success_response(message, status_code=status.HTTP_200_OK, extra_data=None):
    """Create standardized success response"""
    data = {"message": message}
    if extra_data:
        data.update(extra_data)
    return Response(data, status=status_code)


def make_external_api_call(url, method="GET", data=None, headers=None):
    """Make external API call with error handling"""
    try:
        if method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        else:
            response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response, None
    except requests.RequestException as e:
        logger.error(f"External API call failed: {e}")
        return None, str(e)


def serialize_user_data(users):
    """Serialize user data for responses"""
    return [
        {
            "id": user.pk,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "organization": user.organization.id if user.organization else None,
        }
        for user in users
    ]


def sync_user_accounts(organization_id, guid):
    """
    Synchronizes user accounts between external API and local database.

    Handles complex scenarios where users may exist with different identifier combinations:
    - API accounts may have username only, email only, or both
    - DB users may have email only, username only, or both
    - Matches users across different identifier combinations
    - Creates new users when no match is found
    - Detaches users no longer present in external system

    Args:
        organization_id: ID of the organization
        guid: GUID of the vault to sync

    Returns:
        Response object indicating success or failure
    """
    if not all([organization_id, guid]):
        return create_error_response(
            "Missing required parameters: 'organization_id' or 'guid'."
        )

    try:
        company = get_object_or_404(Organization, id=organization_id)
        vault = get_object_or_404(Vault, guid=guid)

        api_url = f"{base_url}/api/UserAccounts/SyncAccounts/{guid}"
        response, error = make_external_api_call(api_url)

        if error:
            return create_error_response(
                f"Failed to fetch data from the external API. Details: {error}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        accounts_data = response.json()

        # Create comprehensive sets of identifiers from API data
        # This handles scenarios where API accounts may have email, username, or both
        synced_emails = set()
        synced_usernames = set()

        for account in accounts_data:
            email = (account.get("emailAddress") or "").strip().lower()
            username = (account.get("userName") or "").strip()

            if email:
                synced_emails.add(email)
            if username:
                synced_usernames.add(username)

        # Detach users no longer present in external data
        # A user should only be detached if NEITHER their email NOR username exists in API
        # This prevents incorrect detachment when a user exists with different identifiers
        linked_users = EDMSUser.objects.filter(vaults=vault)
        for user in linked_users:
            user_email = (user.email or "").strip().lower()
            user_username = (user.username or "").strip()

            # User should be detached if neither their email nor username exists in API data
            should_detach = True
            if user_email and user_email in synced_emails:
                should_detach = False
            elif user_username and user_username in synced_usernames:
                should_detach = False

            if should_detach:
                user.vaults.remove(vault)
                user_vault_id = user.get_user_vault_id(vault)
                if user_vault_id:
                    user_vault_id.delete()

        # Process each account from API
        for account in accounts_data:
            try:
                # Extract account data
                full_name = account.get("fullName", "")
                domain_name = (account.get("domainName") or "").strip()
                user_name = (account.get("userName") or "").strip()
                email = (account.get("emailAddress") or "").strip()
                mfiles_id = account.get("id")
                vault_role = (account.get("vaultRoles") or "").strip()

                # Username is required from API - skip accounts without it
                if not user_name:
                    logger.warning(f"Skipping account with missing username: {account}")
                    continue

                name_parts = full_name.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[-1] if len(name_parts) > 1 else ""

                defaults = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "organization": company,
                    "domain": domain_name,
                    "is_staff": True,
                    "password": make_password(DEFAULT_PASSWORD),
                    "is_admin": vault_role == DOMAIN_VAULT_ROLE_ADMIN,
                    "is_domain_user": bool(domain_name),
                }

                # Smart user lookup strategy:
                # 1. Try to find by email first (if provided)
                # 2. Fall back to username lookup
                # 3. Create new user if no match found
                # This handles scenarios where:
                # - DB user has email, API has matching email + username
                # - DB user has username, API has matching username + email
                # - DB user has both, API has one or both matching
                user = None
                created = False

                # First, try to find by email if provided
                if email:
                    try:
                        user = EDMSUser.objects.get(email=email)
                    except EDMSUser.DoesNotExist:
                        pass

                # If not found by email, try by username
                if not user:
                    try:
                        user = EDMSUser.objects.get(username=user_name)
                    except EDMSUser.DoesNotExist:
                        pass

                # If still not found, create new user
                if not user:
                    create_defaults = {
                        **defaults,
                        "username": user_name,
                        "email": email if email else None,
                    }
                    user = EDMSUser.objects.create(**create_defaults)
                    created = True

                # Update UserVaultID
                user_vault_id = user.get_user_vault_id(vault)
                if user_vault_id:
                    if user_vault_id.mfiles_id != mfiles_id:
                        user_vault_id.mfiles_id = mfiles_id
                        user_vault_id.save()
                else:
                    user_vault_id = UserVaultID.objects.create(
                        vault=vault, mfiles_id=mfiles_id, user=user
                    )

                # Update user fields for existing users (fill in missing data)
                # This handles scenarios where:
                # - DB user had only email, now we have username from API
                # - DB user had only username, now we have email from API
                # - DB user had incomplete profile data
                if not created:
                    updated = False

                    # Update username if it was empty
                    if not user.username and user_name:
                        user.username = user_name
                        updated = True

                    # Update email if it was empty
                    if not user.email and email:
                        user.email = email
                        updated = True

                    # Update other fields if they were empty
                    for field in ["domain", "first_name", "last_name"]:
                        if not getattr(user, field) and defaults.get(field):
                            setattr(user, field, defaults[field])
                            updated = True

                    if updated:
                        user.save()

                # Ensure user has correct status and vault association
                user.is_staff = True
                user.is_active = True
                user.is_domain_user = bool(domain_name)
                user.save()

                # Link user to vault if not already linked
                if not user.vaults.filter(id=vault.id).exists():
                    user.vaults.add(vault)

            except Exception as e:
                identifier = email if email else user_name
                logger.error(
                    f"Error processing account with identifier {identifier}: {e}"
                )
                return create_error_response(
                    f"Error processing account with identifier {identifier}. Details: {e}",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return create_success_response("User accounts synchronized successfully.")

    except Exception as e:
        logger.error(f"Unexpected error in sync_user_accounts: {e}")
        return create_error_response(
            f"Unexpected error occurred. Details: {e}",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class MyTokenObtainPairView(TokenObtainPairView):
    def get_serializer_class(self):
        request = self.request
        auth_type = request.data.get("auth_type") or request.query_params.get(
            "auth_type"
        )  # allow GET or POST

        if auth_type == "username":
            return ExternalAuthTokenSerializer
        else:
            return InternalOrDomainAuthTokenSerializer

# Authentication Views
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def login_activity_post_view(request):
    """Get login activity logs with optional filtering"""
    start_date = request.data.get("start_date")
    end_date = request.data.get("end_date")
    organization_id = request.data.get("organization_id")
    limit = int(request.data.get("limit", DEFAULT_LIMIT))

    logs = LoginLog.objects.select_related("user")

    # Filter by organization if provided
    if organization_id:
        logs = logs.filter(user__organization_id=organization_id)

    # Apply date filters
    if start_date:
        logs = logs.filter(timestamp__gte=start_date)
    if end_date:
        logs = logs.filter(timestamp__lte=end_date)

    logs = logs.order_by("-timestamp")

    # Apply limit if no date filters
    if not start_date and not end_date:
        logs = logs[:limit]

    data = [
        {
            "ip_address": log.ip_address,
            "user": log.user.email,
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "auth_source": log.auth_source,
            "user_agent": log.user_agent,
            "browser": log.browser,
            "os": log.os,
            "device_type": log.device_type,
            "platform": log.platform,
        }
        for log in logs
    ]

    return Response({"activity": data})

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_view(request):
    """Send password reset email"""
    email = request.data.get("email")
    if not email:
        return create_error_response("Email is required")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return create_error_response(
            "User with this email does not exist", status.HTTP_404_NOT_FOUND
        )

    if user.is_domain_user:
        return create_error_response(
            "Please contact your domain admin to reset your password from the organization domain"
        )

    # Generate reset link
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = f"{server_ip}/reset/{uid}/{token}/"

    # Prepare email content
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
            "We've emailed you instructions for setting your password, if an account exists with the email you entered. You should receive them shortly. If you don't receive an email, please make sure you've entered the address you registered with, and check your spam folder."
        )
    else:
        return create_error_response(result["error"])

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """Confirm password reset with token"""
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
    else:
        return create_error_response("Invalid token")

# Organization and Admin Registration
@api_view(["POST"])
def register_company_and_admin(request):
    """Register a new company and its admin user."""
    organization_name = request.data.get("company_name", "").strip().title()
    admin_email = request.data.get("admin_email", "").strip()
    vault_name = request.data.get("vault_name", "").strip()


    normalized_org = organization_name.lower()
    normalized_vault = vault_name.lower()

    # Remove org name prefix if present in vault_name
    if normalized_vault.startswith(normalized_org):
        vault_name = normalized_vault[len(normalized_org):].strip("- ").strip()

    # Fallback if vault_name is empty
    if not vault_name:
        vault_name = "MAIN"

    # Combine and uppercase
    full_vault_name = f"{organization_name}-{vault_name}".upper()

    # Clean up extra hyphens or spaces
    full_vault_name = re.sub(r"\s+", " ", full_vault_name)
    full_vault_name = re.sub(r"-{2,}", "-", full_vault_name).strip("- ")

    if not organization_name or not admin_email:
        return create_error_response("Company name and admin email are required.")

    if Organization.objects.filter(name__iexact=organization_name).exists():
        return create_error_response("An organization with this name already exists.")

    headers = {"Accept": "*/*", "Content-Type": "application/json"}

    try:
        # Step 1: Create vault via external API
        vault_payload = {"vaultName": f"{organization_name}-{vault_name}"}
        vault_url = f"{base_url}/api/Vaults"
        vault_response, error = make_external_api_call(
            vault_url, "POST", vault_payload, headers
        )

        if error or not vault_response.ok:
            logger.error(f"Vault creation failed: {error or vault_response.text}")
            return create_error_response("Failed to create vault.")

        vault_guid = vault_response.json().get("vaultGuid")
        if not vault_guid:
            return create_error_response("Vault GUID not returned from server.")

        # Step 2: Create local organization and vault
        organization = Organization.objects.create(
            name=f"{organization_name.upper()}", email=admin_email, is_active=False
        )
        vault = Vault.objects.create(
            guid=vault_guid,
            name=full_vault_name,
            organization=organization,
        )

        # Step 3: Handle existing user
        existing_user = EDMSUser.objects.filter(email__iexact=admin_email).first()
        if existing_user:
            user_payload = {
                "emailAddress": admin_email,
                "vaultGuid": vault.guid,
            }
            user_api_url = f"{base_url}/api/UserAccounts/AddUser"
            external_response, error = make_external_api_call(
                user_api_url, "POST", user_payload, headers
            )

            if error or not external_response.ok:
                logger.error(
                    f"External user addition failed: {error or external_response.text}"
                )
                return create_error_response("Failed to add existing user to vault.")

            existing_user.vaults.add(vault)
            sync_resp = sync_user_accounts(organization.id, vault.guid)
            if sync_resp.status_code != 200:
                logger.error("Failed to sync the existing user account.")

            return Response(
                {"organization_id": organization.id, "admin_user_id": existing_user.id},
                status=status.HTTP_201_CREATED,
            )

        # Step 4: Create new admin user
        password = generate_random_password()
        admin_user = EDMSUser.objects.create(
            email=admin_email,
            organization=organization,
            first_name=organization_name,
            last_name="Admin",
            is_admin=True,
            is_active=True,
            is_staff=True,
        )
        admin_user.set_password(password)
        admin_user.save()

        # Step 5: Register admin in external system
        external_payload = {
            "fullName": f"Admin {organization_name}",
            "password": password,
            "emailAddress": admin_email,
            "vaultGuid": vault.guid,
            "userID": admin_user.pk,
            "isAdmin": True,
        }
        user_api_url = f"{base_url}/api/UserAccounts/AddUser"
        external_response, error = make_external_api_call(
            user_api_url, "POST", external_payload, headers
        )

        if error or not external_response.ok:
            logger.error(
                f"External user creation failed: {error or external_response.text}"
            )
            admin_user.delete()
            return create_error_response("Failed to register admin user.")

        # Step 6: Associate vault and sync
        admin_user.vaults.add(vault)

        sync_resp = sync_user_accounts(organization.id, vault_guid)
        if sync_resp.status_code != 200:
            logger.error("Failed to sync the new admin account.")

        # Step 7: Send welcome email
        email_body = f"""
        <html>
        <body>
            <p>Dear {admin_user.first_name},</p>
            <p>Your Alignsys EDMS account has been created.</p>
            <p><strong>Temporary Password:</strong> <code>{password}</code></p>
            <p>Please login and reset your password here:</p>
            <p><a href="{server_ip}" style="color: blue; text-decoration: none;">Go to Login</a></p>
            <p>If you did not request this account, please ignore this message.</p>
            <p>Best regards,<br>Alignsys Team</p>
        </body>
        </html>
        """
        email_result = send_email(admin_user.email, email_body)
        if email_result.get("success"):
            logger.info("Welcome email sent successfully.")
        else:
            logger.warning(f"Failed to send welcome email: {email_result.get('error')}")

        return Response(
            {"organization_id": organization.id, "admin_user_id": admin_user.id},
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.exception("Unexpected error in register_company_and_admin")
        return create_error_response("An unexpected error occurred.")

@api_view(["POST"])
def register_vault(request):
    """Register a new company and its admin user."""
    company_id = request.data.get("company_id", "")
    vault_name = request.data.get("vault_name", "").strip()
    admin_email = request.data.get("admin_email", "").strip()
    if not vault_name:
        return create_error_response("Company name and admin email are required.")

    if company_id:
        organization = Organization.objects.get(pk=company_id)
        # Normalize for comparison
        normalized_org = organization.name.lower()
        normalized_vault = vault_name.lower()

        # Remove organization name from vault name if present
        if normalized_org in normalized_vault:
            vault_name = vault_name.lower().replace(normalized_org, "").strip().title()

        # If vault name is now empty, assign default
        if not vault_name:
            vault_name = "Main"

        # Optionally clean up multiple spaces

        vault_name = re.sub(r"\s+", " ", vault_name)

    headers = {"Accept": "*/*", "Content-Type": "application/json"}

    try:
        # Step 1: Create vault via external API
        vault_payload = {"vaultName": f"{organization.name}-{vault_name}"}
        vault_url = f"{base_url}/api/Vaults"
        vault_response, error = make_external_api_call(
            vault_url, "POST", vault_payload, headers
        )

        if error or not vault_response.ok:
            logger.error(f"Vault creation failed: {error or vault_response.text}")
            return create_error_response("Failed to create vault.")

        vault_guid = vault_response.json().get("vaultGuid")
        if not vault_guid:
            return create_error_response("Vault GUID not returned from server.")

        # Step 2: Create local organization and vault

        vault = Vault.objects.create(
            guid=vault_guid,
            name=f"{organization.name}-{vault_name}",
            organization=organization,
        )

        # Step 3: Handle existing user
        existing_user = EDMSUser.objects.filter(email__iexact=admin_email).first()
        if existing_user:
            user_payload = {
                "emailAddress": admin_email,
                "vaultGuid": vault.guid,
            }
            user_api_url = f"{base_url}/api/UserAccounts/AddUser"
            external_response, error = make_external_api_call(
                user_api_url, "POST", user_payload, headers
            )

            if error or not external_response.ok:
                logger.error(
                    f"External user addition failed: {error or external_response.text}"
                )
                return create_error_response("Failed to add existing user to vault.")

            existing_user.vaults.add(vault)
            sync_resp = sync_user_accounts(organization.id, vault.guid)
            if sync_resp.status_code != 200:
                logger.error("Failed to sync the existing user account.")

            return Response(
                {"organization_id": organization.id, "admin_user_id": existing_user.id},
                status=status.HTTP_201_CREATED,
            )

    except Exception as e:
        logger.exception("Unexpected error in register_company_and_admin")
        return create_error_response("An unexpected error occurred.")

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def attach_existing_vault(request):
    """Attach an existing vault to the authenticated user's organization."""
    
    # Input validation
    vault_guid = request.data.get("vault_guid", "").strip()
    if not vault_guid:
        return create_error_response("Vault GUID is required.")
    
    if Vault.objects.filter(guid=vault_guid).exists():
        raise create_error_response(f"Vault with GUID {vault_guid} already exists.")

    try:
        # Get user and organization
        user = request.user
        organization = getattr(user, "organization", None)
        if not organization:
            return create_error_response("User does not belong to an organization.")

        # Fetch vault data from external API
        url = f"{base_url}/api/Vaults/GetVaultGuid/{vault_guid}"
        headers = {"Accept": "*/*", "Content-Type": "application/json"}

        response, error = make_external_api_call(url, "GET", headers)
        if error:
            return create_error_response("Vault Id is invalid, please try a different vaultId")

        # Parse and validate response
        try:
            response_data = response.json()
            if not isinstance(response_data, list) or len(response_data) == 0:
                return create_error_response("Vault does not exist.")
            
            vault_name = response_data[0].get("vaultName")
            if not vault_name:
                return create_error_response("Vault does not exist.")
                
        except (ValueError, KeyError, IndexError):
            return create_error_response("Invalid vault data received.")

        # Check for existing vault name to prevent duplicates
        if Vault.objects.filter(name=vault_name).exists():
            return create_error_response("Vault name already exists.")

        # Create vault
        vault = Vault.objects.create(
            guid=vault_guid,
            name=vault_name,
            organization=organization,
        )

        # Get existing user
        existing_user = EDMSUser.objects.filter(email__iexact=user.email).first()
        if not existing_user:
            return create_error_response("Authenticated user not found in ZenFiles.")

        # Add user to external vault
        user_payload = {
            "emailAddress": existing_user.email,
            "vaultGuid": vault.guid,
        }
        user_api_url = f"{base_url}/api/UserAccounts/AddUser"
        external_response, error = make_external_api_call(
            user_api_url, "POST", user_payload, headers
        )

        if error or not external_response.ok:
            logger.error(f"External user addition failed: {error or external_response.text}")

        # Sync user accounts locally
        sync_resp = sync_user_accounts(organization.id, vault.guid)
        if sync_resp.status_code != 200:
            logger.warning(f"User sync returned status {sync_resp.status_code}")

        # Associate user with vault
        existing_user.vaults.add(vault)

        return Response(
            {
                "organization_id": organization.id, 
                "admin_user_id": existing_user.id,
                "vault_id": vault.id,
                "vault_name": vault.name
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.exception("Unexpected error in attach_existing_vault.")
        return create_error_response("An unexpected error occurred.")

@api_view(["POST"])
def activate_new_organization(request):
    """Activate newly registered organization"""
    organization_id = request.data.get("organization_id")

    if not organization_id:
        return create_error_response("Organization ID is required")

    try:
        organization = get_object_or_404(Organization, id=organization_id)
        users = EDMSUser.objects.filter(organization=organization)

        # vault_creation = register_vault(organization.name)
        if users:
            users.update(is_active=True)
            return create_success_response("Accounts activated successfully.")

    except Exception as e:
        logger.error(f"Error activating organization: {e}")
        return create_error_response("Organization does not exist.")

@api_view(["POST"])
def activate_deactivated_accounts(request, is_active=True):
    """Activate or deactivate user accounts for an organization"""
    organization_id = request.data.get("organization_id")
    activate = request.data.get("action")
    deactivate = request.data.get("action")

    if not organization_id:
        return create_error_response("Organization ID is required")

    try:
        organization = get_object_or_404(Organization, id=organization_id)

        # Check for restricted organizations
        if organization.pk == 1:
            return create_success_response("Accounts have restricted access")

        users = EDMSUser.objects.filter(organization=organization)
        users.update(is_active=is_active)
        organization.is_active = is_active
        organization.save()

        action = "activated" if is_active else "deactivated"
        return create_success_response(f"Accounts {action} successfully.")

    except Exception as e:
        logger.error(f"Error updating account status: {e}")
        return create_error_response("Organization does not exist.")

@api_view(["GET"])
def get_organizations(request):
    """Get all organizations in the system"""
    try:
        organizations = Organization.objects.all()
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error in getting organizations: {e}")
        return Response(
            {
                "success": False,
                "message": "An error occurred while fetching organizations.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_vaults(request):
    """Get vaults accessible to the authenticated user, including vault-specific UserVaultID."""
    user = request.user

    # Get direct and group vaults
    user_vaults = user.vaults.all()
    group_vaults = Vault.objects.filter(user_groups__users=user).distinct()

    # Combine vaults without duplicates
    combined_vaults = list(set(user_vaults) | set(group_vaults))

    vaults_data = []
    for vault in combined_vaults:
        # Ensure the returned UserVaultID belongs to the current vault
        user_vault_id_obj = user.user_vault_ids.filter(vault=vault).first()

        vaults_data.append(
            {
                "name": vault.name,
                "guid": vault.guid,
                "vaultId": user_vault_id_obj.mfiles_id if user_vault_id_obj else None,
            }
        )

    return Response(vaults_data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def organization_vaults(request):
    """Get all vaults for the user's organization"""
    organization = request.user.organization

    organization_vaults = Vault.objects.filter(organization=organization)
    vaults_data = [
        {"name": vault.name, "guid": vault.guid} for vault in organization_vaults
    ]

    return Response(vaults_data, status=status.HTTP_200_OK)


@api_view(["POST"])
def create_vault(request):
    """Create a new vault"""
    vault_name = request.data.get("name")
    organization_id = 1  # TODO: Use request.user.organization_id

    if not all([vault_name, organization_id]):
        return create_error_response("Vault name and organization ID are required.")

    try:
        organization = get_object_or_404(Organization, id=organization_id)

        # Create vault via external API
        data = {"vaultName": vault_name}
        url = f"{base_url}/api/Vaults"
        headers = {"Accept": "*/*", "Content-Type": "application/json"}

        response, error = make_external_api_call(url, "POST", data, headers)
        if error:
            return create_error_response(f"External server error: {error}")

        vault_guid = response.json().get("vaultGuid")
        if not vault_guid:
            return create_error_response("Vault GUID not returned from server.")

        # Create vault and default group
        vault = Vault.objects.create(
            guid=vault_guid, name=vault_name, organization=organization
        )

        # Create default user group
        default_group = UserGroup.objects.create(
            title=ALL_INTERNAL_USERS_GROUP, vault=vault, organization=organization
        )

        # Add all organization users to default group
        organization_users = EDMSUser.objects.filter(organization=organization)
        default_group.users.set(organization_users)

        return Response(
            {
                "id": vault.id,
                "guid": vault.guid,
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error(f"Error creating vault: {e}")
        return create_error_response(str(e))

# User Management Views
class UsersByOrganizationView(generics.ListAPIView):
    serializer_class = EDMSUserSerializer

    def get_queryset(self):
        organization_id = self.kwargs["organization_id"]
        return EDMSUser.objects.filter(
            organization_id=organization_id
        ).select_related("organization")

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_user(request):
    """Register a new user and link them to a vault"""
    data = request.data
    required_fields = ["email", "vaultGuid"]
    missing = [field for field in required_fields if not data.get(field)]

    if missing:
        return create_error_response(f"Missing fields: {', '.join(missing)}")

    email = data["email"].strip()
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    vault_guid = data["vaultGuid"]
    is_admin = data.get("is_admin", False)

    try:
        organization = get_object_or_404(Organization, id=request.user.organization_id)
        vault = get_object_or_404(Vault, guid=vault_guid)

        # ✅ Check if user exists
        existing_user = EDMSUser.objects.filter(email=email).first()

        if existing_user:
            if existing_user.vaults.filter(id=vault.id).exists():
                return create_error_response(
                    "User already exists and is already linked to this vault."
                )

            payload = {
                "emailAddress": email,
                "vaultGuid": vault_guid,
            }
            response, error = make_external_api_call(
                f"{base_url}/api/UserAccounts/AddUser",
                "POST",
                payload,
                headers={"Accept": "*/*", "Content-Type": "application/json"},
            )

            if error or not response.ok:
                logger.error(f"External user attach failed: {error or response.text}")
                return create_error_response(
                    "Failed to attach user to external system."
                )

            existing_user.vaults.add(vault)
            sync_resp = sync_user_accounts(organization.id, vault_guid)
            if sync_resp.status_code != 200:
                logger.error("Account sync after attach failed.")
            return create_success_response(
                "User already existed. Attached to vault.", status.HTTP_200_OK
            )

        # ✅ Create internal user
        user = EDMSUser.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            organization=organization,
            is_staff=True,
            is_active=True,
            is_admin=is_admin,
        )
        new_password = generate_random_password()
        user.set_password(new_password)
        user.save()

        # ✅ Create external user
        external_payload = {
            "fullName": f"{first_name} {last_name}",
            "password": new_password,
            "emailAddress": email,
            "vaultGuid": vault_guid,
            "userID": user.pk,
            "isAdmin": is_admin,
        }
        response, error = make_external_api_call(
            f"{base_url}/api/UserAccounts/AddUser",
            "POST",
            external_payload,
            headers={"Accept": "*/*", "Content-Type": "application/json"},
        )
        if error or not response.ok:
            logger.error(f"External user creation failed: {error or response.text}")
            user.delete()
            return create_error_response("Failed to create user in external system.")

        # ✅ Link user to vault and sync
        user.vaults.add(vault)
        sync_resp = sync_user_accounts(organization.id, vault_guid)
        if sync_resp.status_code != 200:
            logger.error("Account sync after creation failed.")

        # ✅ Send welcome email
        email_body = f"""
        <html>
        <body>
            <p>Dear {first_name},</p>
            <p>Your Alignsys EDMS account has been created.</p>
            <p><strong>Temporary Password:</strong> <code>{new_password}</code></p>
            <p>Please login and reset your password here:</p>
            <p><a href="{server_ip}" style="color: blue; text-decoration: none;">Go to Login</a></p>
            <p>If you did not request this account, please ignore this message.</p>
            <p>Best regards,<br>Alignsys Team</p>
        </body>
        </html>
        """
        email_result = send_email(email, email_body)

        if email_result["success"]:
            logger.info(f"New user {email} registered and email sent.")
            return create_success_response(
                "User registered successfully.", status.HTTP_201_CREATED
            )
        else:
            logger.warning(f"Email to {email} failed: {email_result['error']}")
            return create_error_response("User created, but email sending failed.")

    except Exception as e:
        logger.exception("Unexpected error during user registration.")
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def remove_vault_user(request):
    """
    Remove a user from a vault in the external system, then re-sync accounts.
    """
    data = request.data
    vault_guid = data.get("vaultGuid")
    email = data.get("emailAddress", "").strip()
    organization_id = data.get("organization_id")

    # ✅ Validate required fields
    if not all([vault_guid, email, organization_id]):
        return Response(
            {
                "error": "Missing required fields: 'vaultGuid', 'emailAddress', or 'organization_id'."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        url = f"{base_url}/api/UserAccounts/RemoveVaultUser"
        headers = {"Accept": "*/*", "Content-Type": "application/json"}
        payload = {"vaultGuid": vault_guid, "emailAddress": email}

        response, error = make_external_api_call(
            url, method="POST", data=payload, headers=headers
        )

        if error or not response or response.status_code != 200:
            msg = error or (response.text if response else "No response received.")
            logger.error(f"Failed to remove user from external system: {msg}")
            return Response(
                {"error": f"Failed to remove user from vault. Details: {msg}"},
                status=(
                    response.status_code if response else status.HTTP_502_BAD_GATEWAY
                ),
            )

        # ✅ Sync after successful removal
        sync_result = sync_user_accounts(organization_id, vault_guid)
        if not sync_result or sync_result.status_code != 200:
            logger.error(f"Account sync failed after removal for vault {vault_guid}.")
            # Continue anyway without failing the main operation

        return Response(
            {"message": "User removed and accounts synced successfully."},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.exception("Unexpected error in remove_vault_user")
        return Response(
            {"error": f"Unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

def process_csv_file(csv_file, organization_id):
    """Process CSV file for bulk user registration"""
    errors = []
    users_to_create = []

    try:
        organization = get_object_or_404(Organization, id=organization_id)
    except Exception:
        return 0, ["Organization not found."]

    # Read and parse CSV
    csv_content = csv_file.read().decode("utf-8")
    csv_reader = csv.DictReader(StringIO(csv_content))

    for row in csv_reader:
        email = row.get("email")
        first_name = row.get("first_name")
        last_name = row.get("last_name")
        password = row.get("password")

        # Validate required fields
        if not all([email, first_name, last_name, password]):
            errors.append(f'Missing required fields for user: {email or "unknown"}')
            continue

        try:
            user = EDMSUser(
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,
                organization=organization,
            )
            user.set_password(password)
            users_to_create.append(user)
        except Exception as e:
            errors.append(f"Error creating user {email}: {str(e)}")

    # Bulk create users
    try:
        EDMSUser.objects.bulk_create(users_to_create)

        # Add users to default groups
        created_users = EDMSUser.objects.filter(
            email__in=[user.email for user in users_to_create]
        )

        user_groups = UserGroup.objects.filter(
            title=ALL_INTERNAL_USERS_GROUP, organization=organization
        )

        for user in created_users:
            for user_group in user_groups:
                user_group.users.add(user)

        return len(users_to_create), errors
    except Exception as e:
        logger.error(f"Error in bulk create: {e}")
        return 0, errors + [str(e)]

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def bulk_register_users(request):
    """Bulk register users from CSV file"""
    if "file" not in request.FILES:
        return create_error_response("No file uploaded.")

    file = request.FILES["file"]
    if not file.name.endswith(".csv"):
        return create_error_response("Uploaded file is not a CSV file.")

    # Save and process file
    path = default_storage.save("tmp/" + file.name, ContentFile(file.read()))

    try:
        with default_storage.open(path) as tmp_file:
            user_count, errors = process_csv_file(
                tmp_file, request.user.organization_id
            )
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        default_storage.delete(path)

    if errors:
        error_string = "\n".join(errors)
        return Response(
            {
                "message": f"Processed {user_count} users with errors.",
                "error_message": error_string,
            },
            status=status.HTTP_207_MULTI_STATUS,
        )

    return create_success_response(
        f"Successfully registered {user_count} users.", status.HTTP_201_CREATED
    )

@api_view(["POST"])
def sync_accounts(request):
    """Sync user accounts from external API using helper function"""
    organization_id = request.data.get("organization_id")
    guid = request.data.get("guid")

    return sync_user_accounts(organization_id, guid)

# Vault User Management
@api_view(["POST"])
def assign_user_to_vault(request):
    """Assign user to vault"""
    user_id = request.data.get("user_id")
    vault_id = request.data.get("vault_id")

    if not all([user_id, vault_id]):
        return create_error_response("User ID and Vault ID are required.")

    try:
        user = get_object_or_404(EDMSUser, id=user_id)
        vault = get_object_or_404(Vault, guid=vault_id)

        user.vaults.add(vault)
        return create_success_response("User assigned to vault successfully.")

    except Exception as e:
        logger.error(f"Error assigning user to vault: {e}")
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def detach_user_from_vault(request):
    """Detach user from vault and related groups"""
    user_id = request.data.get("user_id")
    vault_id = request.data.get("vault_id")

    if not all([user_id, vault_id]):
        return create_error_response("User ID and Vault ID are required.")

    try:
        user = get_object_or_404(EDMSUser, id=user_id)
        vault = get_object_or_404(Vault, guid=vault_id)

        # Remove from vault
        user.vaults.remove(vault)

        # Remove from vault groups
        user_groups = UserGroup.objects.filter(vault=vault, users=user)
        for group in user_groups:
            group.users.remove(user)

        return create_success_response(
            "User detached from vault and relevant groups successfully."
        )

    except Exception as e:
        logger.error(f"Error detaching user from vault: {e}")
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def users_not_linked_to_vault(request):
    """Get users not linked to a specific vault"""
    vault_id = request.data.get("vault_id")

    if not vault_id:
        return create_error_response("Vault ID is required.")

    try:
        vault = get_object_or_404(Vault, guid=vault_id)
        organization = vault.organization

        # Get linked users (direct and via groups)
        direct_users = vault.users.all()
        user_groups = UserGroup.objects.filter(vault=vault)
        indirect_users = EDMSUser.objects.filter(user_groups__in=user_groups)

        linked_users = (direct_users | indirect_users).distinct()

        # Get unlinked users
        users_not_linked = EDMSUser.objects.filter(
            organization=organization
        ).exclude(id__in=linked_users)

        return Response(
            serialize_user_data(users_not_linked), status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error getting unlinked users: {e}")
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def users_linked_to_vault(request):
    """Get users linked to a specific vault"""
    vault_id = request.data.get("vault_id")

    if not vault_id:
        return create_error_response("Vault ID is required.")

    try:
        vault = get_object_or_404(Vault, guid=vault_id)

        # Get all linked users
        direct_users = vault.users.all()
        user_groups = UserGroup.objects.filter(vault=vault)
        indirect_users = EDMSUser.objects.filter(user_groups__in=user_groups)

        all_users = (direct_users | indirect_users).distinct()

        # Enhanced serialization with vault-specific data
        user_data = []
        for user in all_users:
            user_vault_id = user.get_user_vault_id(vault)
            user_data.append(
                {
                    "id": user.pk,
                    "username": user.username,
                    "mfiles_id": user_vault_id.mfiles_id if user_vault_id else None,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_staff": user.is_staff,
                    "is_active": user.is_active,
                    "is_admin": user.is_admin,
                    "organization": user.organization.id if user.organization else None,
                }
            )

        return Response(user_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting linked users: {e}")
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

# Group Management
@api_view(["POST"])
def vault_groups(request):
    """Get all groups for a specific vault"""
    guid = request.data.get("vault_guid")

    if not guid:
        return create_error_response("Vault GUID is required.")

    try:
        vault = get_object_or_404(Vault, guid=guid)
        user_groups = UserGroup.objects.filter(vault=vault).prefetch_related("users")

        user_groups_data = []
        for group in user_groups:
            users_data = serialize_user_data(group.users.all())
            user_groups_data.append(
                {
                    "id": group.id,
                    "title": group.title,
                    "vault": group.vault.id if group.vault else None,
                    "users": users_data,
                }
            )

        return Response(user_groups_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting vault groups: {e}")
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def users_linked_to_vault_not_in_group(request):
    """Get users linked to vault but not in a specific group"""
    vault_id = request.data.get("vault_id")
    group_id = request.data.get("group_id")

    if not all([vault_id, group_id]):
        return create_error_response("Vault ID and Group ID are required.")

    try:
        vault = get_object_or_404(Vault, guid=vault_id)
        user_group = get_object_or_404(UserGroup, id=group_id)

        # Get vault users excluding group members
        users_linked_to_vault = EDMSUser.objects.filter(vaults=vault)
        users_in_group = user_group.users.all()

        users_not_in_group = users_linked_to_vault.exclude(
            pk__in=users_in_group.values_list("pk", flat=True)
        )

        return Response(
            serialize_user_data(users_not_in_group), status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error getting users not in group: {e}")
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def add_user_to_group(request):
    """Add user to group"""
    user_id = request.data.get("user_id")
    group_id = request.data.get("group_id")

    if not all([user_id, group_id]):
        return create_error_response("User ID and Group ID are required.")

    try:
        user = get_object_or_404(EDMSUser, id=user_id)
        group = get_object_or_404(UserGroup, id=group_id)

        group.users.add(user)
        return create_success_response(
            f"User {user.first_name} {user.last_name} added to group {group.title}."
        )

    except Exception as e:
        logger.error(f"Error adding user to group: {e}")
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def remove_user_from_group(request):
    """Remove user from group"""
    user_id = request.data.get("user_id")
    group_id = request.data.get("group_id")

    if not all([user_id, group_id]):
        return create_error_response("User ID and Group ID are required.")

    try:
        user = get_object_or_404(EDMSUser, id=user_id)
        group = get_object_or_404(UserGroup, id=group_id)

        group.users.remove(user)
        return create_success_response(
            f"User {user.first_name} {user.last_name} removed from group {group.title}."
        )

    except Exception as e:
        logger.error(f"Error removing user from group: {e}")
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

# Event Logging
@api_view(["POST"])
def create_log(request):
    """Create event log entry"""
    serializer = EventLogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
def get_logs(request):
    """Get all event logs"""
    logs = EventLog.objects.all()
    serializer = EventLogSerializer(logs, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def get_log_by_id(request, event_id):
    """Get specific event log by ID"""
    try:
        log = get_object_or_404(EventLog, event_id=event_id)
        serializer = EventLogSerializer(log)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error getting log: {e}")
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
def get_user_vault_id(request):
    """Get user's vault ID for a specific vault"""
    user_id = request.data.get("user_id")
    guid = request.data.get("guid")

    if not all([user_id, guid]):
        return create_error_response("User ID and Vault GUID are required.")

    try:
        user = get_object_or_404(EDMSUser, id=user_id)
        vault = get_object_or_404(Vault, guid=guid)

        user_vault_id = user.get_user_vault_id(vault)
        if not user_vault_id:
            return create_error_response(
                f"UserVaultID not found for {user.first_name} {vault.guid}",
                status.HTTP_404_NOT_FOUND,
            )

        response = {
            "vaultName": vault.name,
            "vaultGuid": vault.guid,
            "mfilesID": user_vault_id.mfiles_id,
        }
        return Response(response, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting user vault ID: {e}")
        return create_error_response("Not found", status.HTTP_404_NOT_FOUND)
