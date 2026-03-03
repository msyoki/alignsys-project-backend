"""
Authentication and Subscription Management Views

This module contains all API endpoints for:
- Authentication (login, register, token refresh, validation)
- Trial Management (status, conversion, cancellation, history)
- Subscription Management (creation, updates)
- Organization User Management
- Payment Webhooks

Organization:
1. Authentication Views (Public)
2. Trial Management Views (Authenticated)
3. Subscription Management Views (Authenticated/Admin)
4. Webhook Views (Public with validation)
5. Organization Management Views (Admin only)
"""

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from pydantic_core import ValidationError
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.db.models import Q


from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
import logging
import datetime
import uuid
from django.db.models import Q

logger = logging.getLogger(__name__)


from .serializers import (
    LoginRequestSerializer, 
    TokenResponseSerializer, 
    RefreshRequestSerializer,
    RegisterRequestSerializer, 
    RegisterResponseSerializer, 
    SubscriptionRequestSerializer,
    AddOrgUserRequestSerializer,
    VerifyEmailRequestSerializer,
    VerifyEmailResponseSerializer,
    ResendVerificationRequestSerializer,
    ResendVerificationResponseSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestResponseSerializer,
    PasswordResetConfirmResponseSerializer,
    CustomTokenObtainPairSerializer
)
from .models import (
    Profile,
    Subscription,
    UserType,
    SubscriptionStatus,
    BillingInterval,
    PlanName,
    SubscriptionEvent
)
from .utils import (
    get_user_by_identifier, 
    create_org_user, 
    build_register_response, 
    validate_jwt_token,
    normalize_plan_name,
    normalize_billing_interval,
    can_start_trial,
    create_trial_history,
    convert_trial_to_active,
    cancel_trial,
    get_trial_status,
    get_trial_history,
    generate_unique_username,
    normalize_subscription_status,
    determine_subscription_event
)
from django.shortcuts import get_object_or_404
from .services.license_service import LicenseService
from rest_framework.response import Response
from .authentication import JWTAuthentication, build_user_payload, get_tokens_for_user

User = get_user_model()


@extend_schema(tags=["Authentication"])
class CurrentUserView(APIView):
    """
    Returns the currently authenticated user info.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id if hasattr(user, "id") else None,
            "email": user.email if hasattr(user, "email") else None,
            "phone": user.phone if hasattr(user, "phone") else None ,
            "username": user.username if hasattr(user, "username") else None,
            "first_name": user.first_name if hasattr(user, "first_name") else None,
            "last_name": user.last_name if hasattr(user, "last_name") else None,
            "is_active": user.is_active if hasattr(user, "is_active") else None,
            "is_admin": getattr(user, "is_admin", False),
            "is_super_admin" : getattr(user, "is_super_admin", False),
            "profile": getattr(user, "profile_id", None),
            # add any other claims your documents project expects
        })

# ============================================================================
# SECTION 1: AUTHENTICATION VIEWS (Public Access)
# ============================================================================

@extend_schema(
    summary="User Login",
    description="""
Authenticate a user with email/username and password. Returns JWT tokens.

**Authentication:** None required (public endpoint)

**Request Body:**
- `username` (string, required): Email address or username
- `password` (string, required): User password

**Response:**
- `access` (string): JWT access token (short-lived, ~15 minutes)
- `refresh` (string): JWT refresh token (long-lived, ~7 days)
- `token_type` (string): Always "bearer"
- `user` (object): User profile information including subscription details
""",
    request=LoginRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=TokenResponseSerializer,
            description="Login successful",
            examples=[
                OpenApiExample(
                    "Successful Login",
                    value={
                        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "email": "john.doe@example.com",
                            "username": "johndoe",
                            "first_name": "John",
                            "last_name": "Doe",
                            "is_admin": False,
                            "profile": {
                                "id": "123e4567-e89b-12d3-a456-426614174001",
                                "name": "John Doe",
                                "type": "INDIVIDUAL",
                                "subscription": {
                                    "plan_name": "ESIGN",
                                    "status": "active"
                                }
                            }
                        }
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(description="Invalid request data"),
        401: OpenApiResponse(
            description="Invalid credentials",
            examples=[
                OpenApiExample(
                    "Invalid Credentials",
                    value={"detail": "Invalid credentials"},
                    response_only=True
                )
            ]
        )
    },
    examples=[
        OpenApiExample(
            "Login with Email",
            value={"username": "john.doe@example.com", "password": "MySecurePassword123!"},
            request_only=True
        ),
        OpenApiExample(
            "Login with Username",
            value={"username": "johndoe", "password": "MySecurePassword123!"},
            request_only=True
        )
    ],
    tags=["Authentication"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """User Login Endpoint with License Validation"""
    serializer = LoginRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    identifier = serializer.validated_data['username'].strip()
    password = serializer.validated_data['password'].strip()
    
    user = get_user_by_identifier(identifier)
    if not user or not check_password(password, user.password):
        return Response(
            {'detail': 'Invalid credentials'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check if user is active
    if not user.is_active:
        return Response(
            {'detail': 'Account is deactivated'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # CHECK LICENSE - This is the key validation
    if not user.has_license:
        return Response(
            {
                'detail': 'No license assigned to this user. Please contact your administrator.',
                'error_code': 'NO_LICENSE',
                'user_id': str(user.id)
            }, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get the subscription safely
    
    subscription = user.profile.subscriptions.filter(
        status__in=[
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,  # optional depending on your logic
        ]
    ).first()

    # Check if subscription exists and is active
    if not subscription or subscription.status not in ['active', 'trialing']:
        return Response(
            {
                'profile_id': str(user.profile.id),
                'profile_name': user.profile.name,
                'detail': 'Profile subscription is not active',
                'error_code': 'SUBSCRIPTION_INACTIVE'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    # All checks passed - issue tokens
    refresh = CustomTokenObtainPairSerializer.get_token(user)

    response_data = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'token_type': 'bearer',
        'user': build_user_payload(user),
    }

    return Response(response_data, status=status.HTTP_200_OK)

@extend_schema(
    summary="Refresh Access Token",
    description="""
Generate a new access token using a valid refresh token.

This endpoint:
- Issues a new access token
- Rotates the refresh token for security
- Returns basic user information

**Authentication:** None required (refresh token provided in request body)

**Request Body**
- `refresh` (string, required): Valid JWT refresh token

**Response**
- `access` (string): New JWT access token
- `refresh` (string): New rotated refresh token
- `token_type` (string): Token type (always `bearer`)
- `user` (object): Basic user profile information

**Security Notes**
- Refresh tokens are single-use and rotated on each request
- The previous refresh token becomes invalid after use
""",
    request=RefreshRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=TokenResponseSerializer,
            description="Token refreshed successfully",
            examples=[
                OpenApiExample(
                    "Successful Token Refresh",
                    value={
                        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "email": "john.doe@example.com",
                            "username": "johndoe"
                        }
                    },
                    response_only=True,
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid request data"
        ),
        401: OpenApiResponse(
            description="Invalid or expired refresh token",
            examples=[
                OpenApiExample(
                    "Invalid Refresh Token",
                    value={"detail": "Invalid or expired refresh token"},
                    response_only=True,
                )
            ]
        ),
    },
    examples=[
        OpenApiExample(
            "Refresh Token Request",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            request_only=True,
        ),
    ],
    tags=["Authentication"]
)

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_view(request):
    """Token Refresh Endpoint"""
    serializer = RefreshRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    refresh_token_str = serializer.validated_data['refresh']
    try:
        refresh = RefreshToken(refresh_token_str)
        user = User.objects.get(id=refresh.payload['user_id'])
    except Exception:
        return Response({'detail': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

    new_refresh = RefreshToken.for_user(user)
    response_data = {
        'access': str(new_refresh.access_token),
        'refresh': str(new_refresh),
        'token_type': 'bearer',
        'user': build_user_payload(user)
    }

    return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(
    summary="User Registration",
    description="""
Register a new user account (Individual or Organization).

**Authentication:** Public (no auth required)

### Email Verification
- A verification email is sent after successful registration
- Account remains inactive until verified
- Verification link expires after 24 hours
- Registration is rolled back if email delivery fails

### Profile Types
- **INDIVIDUAL** – Personal account (default)
- **ORGANIZATION** – Business/team account with admin privileges

### Request Fields
- **email** (string, required): Unique email address
- **password** (string, required): User password
- **first_name** (string, required)
- **last_name** (string, required)
- **profile_type** (string, optional): INDIVIDUAL | ORGANIZATION (default: INDIVIDUAL)
- **org_name** (string, required if profile_type=ORGANIZATION)

### Response Fields
- **id** (string): User UUID
- **email** (string): User email
- **username** (string): Generated username
- **profile_id** (string): Profile UUID
- **profile_type** (string): INDIVIDUAL | ORGANIZATION
- **message** (string): Verification instructions
""",
    request=RegisterRequestSerializer,
    responses={
        201: OpenApiResponse(
            response=RegisterResponseSerializer,
            description="User registered successfully. Verification email sent.",
            examples=[
                OpenApiExample(
                    "Registration Success",
                    value={
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "john.doe@example.com",
                        "username": "johndoe482",
                        "profile_id": "123e4567-e89b-12d3-a456-426614174001",
                        "profile_type": "INDIVIDUAL",
                        "message": "Registration successful! Please check your email to verify your account."
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Invalid request or registration not allowed",
            examples=[
                OpenApiExample(
                    "Email Already Exists",
                    value={
                        "detail": "An account with this email already exists. Please login or use a different email address.",
                        "email": "user@example.com",
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Email Not Verified",
                    value={
                        "detail": (
                            "An account with this email already exists but has not been verified. "
                            "Please check your email for the verification link."
                        ),
                        "email": "user@example.com",
                        "can_resend": True,
                    },
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Register Individual",
            value={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
                "profile_type": "INDIVIDUAL",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Register Organization",
            value={
                "email": "admin@acme.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
                "profile_type": "ORGANIZATION",
                "org_name": "Acme Corp",
            },
            request_only=True,
        ),
    ],
    tags=["Authentication"],
)

@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def register_view(request):
    """User Registration Endpoint with Email Verification"""
    serializer = RegisterRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Normalize email / username
    email = data['email'].strip().lower()

    # Check if user with this email already exists
    if User.objects.filter(email=email).exists():
        existing_user = User.objects.get(email=email)
        
        # If user exists but hasn't verified email
        if not existing_user.is_active and not existing_user.email_verified:
            # Check if verification token has expired
            if existing_user.email_verification_token_expires and \
               existing_user.email_verification_token_expires < timezone.now():
                return Response(
                    {
                        "detail": "An account with this email exists but was not verified. Please use the resend verification endpoint to get a new verification link.",
                        "email": email,
                        "can_resend": True
                    },
                    status=status.HTTP_409_CONFLICT
                )
            else:
                return Response(
                    {
                        "detail": "An account with this email already exists but has not been verified. Please check your email for the verification link.",
                        "email": email,
                        "can_resend": True
                    },
                    status=status.HTTP_409_CONFLICT
                )
        else:
            # User exists and is verified/active
            return Response(
                {
                    "detail": "An account with this email already exists. Please login or use a different email address.",
                    "email": email
                },
                status=status.HTTP_409_CONFLICT
            )
    
    # Randonmly generate username if taken
    username = generate_unique_username(data['first_name'], data['last_name'])

   
    # Normalize USER TYPE
    raw_type = data.get('profile_type')
    print("Raw Type:", raw_type)
    if isinstance(raw_type, UserType):
        user_type = raw_type
    else:
        raw_type = str(raw_type).upper()
        try:
            user_type = UserType(raw_type)
        except ValueError:
            user_type = UserType.INDIVIDUAL

    # Prepare profile instance (not saved yet)
    profile_name = (
        f"{data['first_name'].strip()} {data['last_name'].strip()}"
        if user_type == UserType.INDIVIDUAL
        else data.get('org_name', '').strip()
    )
    profile = Profile(
        name=profile_name,
        type=user_type,
        org_name=data.get('org_name') if user_type == UserType.ORGANIZATION else None
    )

    # Normalize plan name
    # try:
    #     plan_name = normalize_plan_name(data['plan_name'])
    # except ValueError as e:
    #     profile.delete()
    #     return Response(
    #         {"detail": str(e)},
    #         status=status.HTTP_400_BAD_REQUEST
    #     )

    # Get subscription status from request (default to ACTIVE)
    # subscription_status = data.get('status', SubscriptionStatus.ACTIVE)
    
    # If user is signing up for a trial, check if they're eligible
    # if subscription_status == SubscriptionStatus.TRIALING:
    #     can_trial, error_message = can_start_trial(profile, plan_name)
    #     if not can_trial:
    #         profile.delete()
    #         return Response(
    #             {"detail": error_message},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    # Determine billing interval
    # if plan_name in [PlanName.ESIGN, PlanName.EDMS_PLUS] and subscription_status != SubscriptionStatus.TRIALING:
    #     try:
    #         billing_interval = normalize_billing_interval(data.get('billing_interval'))
    #     except ValueError as e:
    #         profile.delete()
    #         return Response(
    #             {"detail": str(e)},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    # else:
    #     billing_interval = BillingInterval.NONE

    # Create Subscription
    # subscription = Subscription.objects.create(
    #     profile=profile,
    #     plan_name=plan_name,
    #     status=subscription_status,
    #     billing_interval=billing_interval,
    #     no_of_licenses=5 if user_type == UserType.ORGANIZATION else 1
    # )

    # Create trial history if this is a trial signup
    # if subscription_status == SubscriptionStatus.TRIALING:
    #     create_trial_history(profile, plan_name, subscription)


    # Prepare user instance (not saved yet)
    user = User(
        email=email,
        username=username,
        first_name=data['first_name'].strip(),
        last_name=data['last_name'].strip(),
        password=data['password'],  # Will be hashed by set_password below
        is_domain_user=data.get('is_domain_user', False),
        domain=data.get('domain'),
        profile=profile,
        is_admin=user_type == UserType.ORGANIZATION,
        is_active=False  # User inactive until email verified
    )
    user.set_password(data['password'])

    # Generate verification token
    verification_token = get_random_string(64)
    token_expiry = timezone.now() + timedelta(hours=24)
    user.email_verification_token = verification_token
    user.email_verification_token_expires = token_expiry
  

    # Send verification email
    try:
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        email_subject = "Welcome! Please verify your email"
        email_body = f"""
            Hello {user.first_name},

            Welcome to our Alignsys! We're excited to have you on board.

            Please verify your email address by clicking the link below:

            {verification_url}

            This link will expire in 24 hours.

            Your account details:
            - Email: {user.email}
            - Username: {user.username}
    

            If you didn't create this account, please ignore this email.

            Best regards,
            The Team
        """
        
        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        
        logger.info(f"Verification email sent successfully to {user.email}")
        profile.save()
        user.save()
        
    except Exception as e:
        # If email fails to send, rollback the transaction
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        # Transaction will be automatically rolled back due to @transaction.atomic
        return Response(
            {"detail": "Failed to send verification email. Please check your email address and try again."},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,    
            "profile_id": str(profile.id),
            "profile_type": profile.type,
            "has_license": user.has_license,  # NEW: Include license status in response
            # "subscription_plan": subscription.plan_name,
            # "subscription_status": subscription.status,
            "message": "Registration successful! Please check your email to verify your account."
        },
        status=status.HTTP_201_CREATED
    )


@extend_schema(
    summary="Verify Email",
    description="""
Verify a user's email address using the token sent during registration.

**Authentication:** None required (public endpoint)

**Process:**
1. User clicks verification link in email
2. Token is validated
3. User account is activated
4. User can now log in

**Request Body:**
- `token` (string, required): Email verification token from the email link

**Response:**
- Success message confirming email verification
""",
    request=VerifyEmailRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=VerifyEmailResponseSerializer,
            description="Email verified successfully",
            examples=[
                OpenApiExample(
                    "Successful Verification",
                    value={
                        "message": "Email verified successfully! You can now log in.",
                        "email": "user@example.com"
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Invalid or expired token",
            examples=[
                OpenApiExample(
                    "Invalid Token",
                    value={"detail": "Invalid or expired verification token"},
                    response_only=True,
                ),
                OpenApiExample(
                    "Already Verified",
                    value={"detail": "Email already verified"},
                    response_only=True,
                ),
            ],
        ),
    },
    tags=["Authentication"],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_view(request):
    """Email Verification Endpoint"""
    token = request.data.get('token')
    
    if not token:
        return Response(
            {"detail": "Verification token is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(
            email_verification_token=token,
            email_verification_token_expires__gt=timezone.now()
        )
        
        if user.is_active:
            return Response(
                {"detail": "Email already verified"},
                status=status.HTTP_400_BAD_REQUEST
            )

   
        # Activate user account
        user.is_active = True
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires = None
        user.has_license = True  # Optionally assign a default license upon verification
        user.license_assigned_at = timezone.now()  # Track when license was assigned
        user.save()
        
        logger.info(f"Email verified successfully for user: {user.email}")

        # Issue tokens like login_view
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        response_data = {
            'message': 'Email verified successfully! You can now log in.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'token_type': 'bearer',
            'user': build_user_payload(user),
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response(
            {"detail": "Invalid or expired verification token"},
            status=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    summary="Resend Verification Email",
    description="""
Resend a verification email to users who haven't verified their email yet.

**Authentication:** None required (public endpoint)

**Use Cases:**
- User didn't receive the original email
- Verification link expired (24 hours)
- Email was accidentally deleted

**Request Body:**
- `email` (string, required): User email address

**Response:**
- Success message confirming email was resent
""",
    request=ResendVerificationRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=ResendVerificationResponseSerializer,
            description="Verification email resent successfully",
            examples=[
                OpenApiExample(
                    "Email Resent",
                    value={"message": "Verification email has been resent. Please check your inbox."},
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Invalid request",
            examples=[
                OpenApiExample(
                    "Already Verified",
                    value={"detail": "Email already verified"},
                    response_only=True,
                ),
                OpenApiExample(
                    "User Not Found",
                    value={"detail": "No account found with this email address"},
                    response_only=True,
                ),
            ],
        ),
    },
    tags=["Authentication"],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email_view(request):
    """Resend Email Verification Endpoint"""
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response(
            {"detail": "Email address is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(email=email)
        
        if user.is_active:
            return Response(
                {"detail": "Email already verified"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate new verification token
        verification_token = get_random_string(64)
        token_expiry = timezone.now() + timedelta(hours=24)
        
        user.email_verification_token = verification_token
        user.email_verification_token_expires = token_expiry
        user.save()
        
        # Send verification email
        try:
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
            
            email_subject = "Verification Email - Resent"
            email_body = f"""
        Hello {user.first_name},

        You requested a new verification link for your account.

        Please verify your email address by clicking the link below:

        {verification_url}

        This link will expire in 24 hours.

        If you didn't request this, please ignore this email.

        Best regards,
        The Team
            """
            
            send_mail(
                subject=email_subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"Verification email resent successfully to {user.email}")
            
            return Response(
                {"message": "Verification email has been resent. Please check your inbox."},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Failed to resend verification email to {user.email}: {str(e)}")
            return Response(
                {"detail": "Failed to send verification email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except User.DoesNotExist:
        # Don't reveal if email exists for security reasons
        return Response(
            {"message": "If an account exists with this email, a verification link has been sent."},
            status=status.HTTP_200_OK
        )

@extend_schema(
    summary="Validate JWT Token",
    description="""
Validate the JWT access token provided in the Authorization header.

This endpoint:
- Confirms the token is valid
- Ensures the user's email is verified
- Returns basic user and profile information

**Authentication:** Bearer token required  

**Headers**
- `Authorization`: Bearer <access_token>

**Email Verification Rules**
- Users must verify their email before accessing protected APIs
- Unverified users receive a 403 response
- Verification emails can be resent using the resend verification endpoint

**Response**
- `valid` (boolean): Indicates whether the token is valid
- `user` (object): User and profile information (if valid)
""",
    request=None,
    responses={
        200: OpenApiResponse(
            description="Token is valid and email is verified",
            examples=[
                OpenApiExample(
                    "Valid Token",
                    value={
                        "valid": True,
                        "user": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "email": "john.doe@example.com",
                            "username": "johndoe",
                            "email_verified": True,
                            "profile": {
                                "id": "123e4567-e89b-12d3-a456-426614174001",
                                "name": "John Doe",
                                "type": "INDIVIDUAL"
                            }
                        }
                    },
                    response_only=True,
                )
            ]
        ),
        401: OpenApiResponse(
            description="Invalid or missing token",
            examples=[
                OpenApiExample(
                    "Unauthorized",
                    value={"detail": "Invalid or missing token"},
                    response_only=True,
                )
            ]
        ),
        403: OpenApiResponse(
            description="Email not verified",
            examples=[
                OpenApiExample(
                    "Email Not Verified",
                    value={
                        "detail": "Email not verified. Please check your email for the verification link.",
                        "email_verified": False
                    },
                    response_only=True,
                )
            ]
        ),
    },
    tags=["Authentication"]
)
@api_view(['GET'])
@permission_classes([AllowAny])
def validate_token_view(request):
    """Token Validation Endpoint"""
    auth = JWTAuthentication()
    auth_result = auth.authenticate(request)
    
    if not auth_result:
        return Response(
            {'detail': 'Invalid or missing token'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    validated_user = auth_result[0]
    
    # Check if user's email is verified
    # if not validated_user.is_active or not getattr(validated_user, 'email_verified', False):
    #     return Response(
    #         {
    #             'detail': 'Email not verified. Please check your email for the verification link.',
    #             'email_verified': False,
    #             'email': validated_user.email
    #         },
    #         status=status.HTTP_403_FORBIDDEN
    #     )
    
    return Response({
        'valid': True,
        'user': build_user_payload(validated_user)
    }, status=status.HTTP_200_OK)

@extend_schema(
    summary="Request Password Reset",
    description="""
Request a password reset link via email.

**Authentication:** None required (public endpoint)

**Process:**
1. User provides their email address.
2. System sends a password reset link if the account exists.
3. Reset link expires after 1 hour.
4. Same response is returned whether the email exists or not, for security.

**Request Body:**
- `email` (string, required): Email address of the account.

**Response:**
- Always returns a success message for security.
""",
    request=PasswordResetRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=PasswordResetRequestResponseSerializer,
            description="Password reset email sent (or email doesn't exist)",
            examples=[
                OpenApiExample(
                    'Password Reset Requested',
                    value={
                        'message': 'If an account exists with this email, a password reset link has been sent.'
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Invalid request",
            examples=[
                OpenApiExample(
                    'Missing Email',
                    value={'detail': 'Email address is required'},
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            'Request Password Reset',
            value={'email': 'user@example.com'},
            request_only=True,
        ),
    ],
    tags=['Authentication'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request_view(request):
    """Request Password Reset Endpoint"""
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email'].strip().lower()
    
    try:
        user = User.objects.get(email=email)
        
        # Only send reset email if account is active
        if user.is_active:
            # Generate password reset token
            reset_token = get_random_string(64)
            token_expiry = timezone.now() + timedelta(hours=1)
            
            user.password_reset_token = reset_token
            user.password_reset_token_expires = token_expiry
            user.save()
            
            # Send password reset email
            try:
                reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
                
                email_subject = "Password Reset Request"
                email_body = f"""
                        Hello {user.first_name},

                        You requested to reset your password for your account.

                        Please click the link below to reset your password:

                        {reset_url}

                        This link will expire in 1 hour.

                        If you didn't request this password reset, please ignore this email and your password will remain unchanged.

                        For security reasons, never share this link with anyone.

                        Best regards,
                        The Team
                """
                
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                
                logger.info(f"Password reset email sent to {user.email}")
                
            except Exception as e:
                logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        
    except User.DoesNotExist:
        # Don't reveal if email exists for security reasons
        logger.info(f"Password reset requested for non-existent email: {email}")
    
    # Always return same response for security
    return Response(
        {
            "message": "If an account exists with this email, a password reset link has been sent."
        },
        status=status.HTTP_200_OK
    )

@extend_schema(
    summary="Confirm Password Reset",
    description="""
Reset password using the token received via email.

**Authentication:** None required (public endpoint)

**Process:**
1. User provides reset token and new password.
2. Token is validated (must not be expired).
3. Password is updated.
4. User can login with new password.

**Security Notes:**
- Token expires after 1 hour.
- Token can only be used once.
- Password must be at least 8 characters.
- Passwords must match.

**Request Body:**
- `token` (string, required): Password reset token from email.
- `new_password` (string, required): New password (minimum 8 characters).
- `confirm_password` (string, required): Confirm new password.

**Response:**
- Success message confirming password reset.
""",
    request=PasswordResetConfirmSerializer,
    responses={
        200: OpenApiResponse(
            response=PasswordResetConfirmResponseSerializer,
            description="Password reset successful",
            examples=[
                OpenApiExample(
                    'Password Reset Successful',
                    value={
                        'message': 'Password has been reset successfully. You can now login with your new password.'
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Invalid token or validation error",
            examples=[
                OpenApiExample(
                    'Invalid Token',
                    value={'detail': 'Invalid or expired password reset token'},
                    response_only=True,
                ),
                OpenApiExample(
                    'Passwords Do Not Match',
                    value={'confirm_password': ['Passwords do not match']},
                    response_only=True,
                ),
                OpenApiExample(
                    'Password Too Short',
                    value={'new_password': ['Ensure this field has at least 8 characters.']},
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            'Reset Password',
            value={
                'token': 'abc123def456...',
                'new_password': 'NewSecurePass123!',
                'confirm_password': 'NewSecurePass123!'
            },
            request_only=True,
        ),
    ],
    tags=['Authentication'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def password_reset_confirm_view(request):
    """Confirm Password Reset Endpoint"""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']
    
    try:
        user = User.objects.get(
            password_reset_token=token,
            password_reset_token_expires__gt=timezone.now()
        )
        
        # Set new password
        user.set_password(new_password)
        
        # Clear reset token
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.save()
        
        logger.info(f"Password reset successful for user: {user.email}")
        
        return Response(
            {
                "message": "Password has been reset successfully. You can now login with your new password."
            },
            status=status.HTTP_200_OK
        )
        
    except User.DoesNotExist:
        return Response(
            {"detail": "Invalid or expired password reset token"},
            status=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    summary="Change password",
    description="""
Change the password for the currently authenticated user.

**Authentication**
- Bearer token required

**Rules**
- User must be authenticated
- Current password is required for verification
- New password must be confirmed
""",
    request=PasswordResetRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Password changed successfully",
            examples=[
                OpenApiExample(
                    "Password Changed",
                    value={"message": "Password changed successfully"},
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Validation error",
            examples=[
                OpenApiExample(
                    "Incorrect Current Password",
                    value={"detail": "Current password is incorrect"},
                    response_only=True,
                ),
                OpenApiExample(
                    "Passwords Do Not Match",
                    value={"detail": "New passwords do not match"},
                    response_only=True,
                ),
            ],
        ),
        401: OpenApiResponse(
            description="Authentication required",
            examples=[
                OpenApiExample(
                    "Not Authenticated",
                    value={"detail": "Authentication credentials were not provided."},
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Change Password",
            value={
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!",
            },
            request_only=True,
        ),
    ],
    tags=["Authentication"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Change Password Endpoint (Authenticated Users)"""
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        return Response(
            {"detail": "All password fields are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if new_password != confirm_password:
        return Response(
            {"detail": "New passwords do not match"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(new_password) < 8:
        return Response(
            {"detail": "Password must be at least 8 characters long"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    
    # Verify current password
    if not user.check_password(current_password):
        return Response(
            {"detail": "Current password is incorrect"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Set new password
    user.set_password(new_password)
    user.save()
    
    logger.info(f"Password changed for user: {user.email}")
    
    return Response(
        {"message": "Password changed successfully"},
        status=status.HTTP_200_OK
    )



# ============================================================================
# SECTION 2: SUBSCRIPTION MANAGEMENT VIEWS
# ============================================================================

@extend_schema(
    summary="Create Subscription",
    description="""
Create a subscription for a profile.

This endpoint:
- Normalizes plan name and billing interval
- Validates trial eligibility when status is `TRIALING`
- Supports both trial and paid subscriptions pending payment details
- Optionally assigns licenses

**Authentication:** None required (public endpoint)

---

### Request Body

**Common Fields (All Subscriptions)**  
- `profile_id` (string, UUID, required): Profile to attach the subscription to  
- `plan_name` (string, required): Subscription plan name  
- `status` (string, required): Subscription status  
- `start_date` (datetime, optional): Subscription start date  
- `trial_end` (datetime, optional): Trial end date  
- `current_period_end` (datetime, optional): Billing or trial period end date  
- `cancel_at` (datetime, optional): Scheduled cancellation date  
- `cancel_at_period_end` (boolean, optional): Cancel at period end  
- `no_of_licenses` (integer, required): Number of licenses  
- `pending_number_of_licenses` (integer, optional): Pending license change  

---

**Paid Subscription Fields (status ≠ TRIALING)**  
- `setup_intent_id` (string, optional): Stripe setup intent ID  
- `stripe_subscription_id` (string, optional): Stripe subscription ID  
- `billing_interval` (string, required): Billing interval (e.g., MONTHLY, YEARLY)  
- `pending_billing_interval` (string, optional): Pending billing interval change  

---

**Trial Subscription Rules (status = TRIALING)**  
- Billing interval is automatically set to `NONE`  
- Stripe fields are not required  

---

### Allowed Billing Interval Values
- `MONTHLY`
- `YEARLY`

---


### Allowed Plan_name Values
- `FREE_ESIGN`
- `ESIGN`
- `EDMS_PLUS`


---

### Allowed Status Values
- `INCOMPLETE`
- `INCOMPLETE_EXPIRED`
- `TRIALING`
- `ACTIVE`
- `PAST_DUE`
- `CANCELED`
- `UNPAID`
""",
    request=SubscriptionRequestSerializer,
    responses={
        201: OpenApiResponse(
            description="Subscription created successfully",
            examples=[
                OpenApiExample(
                    "Successful Trial Subscription",
                    value={
                        "detail": "Subscription created successfully",
                        "subscription": {
                            "id": "123e4567-e89b-12d3-a456-426614174001",
                            "profile_id": "123e4567-e89b-12d3-a456-426614174001",
                            "plan_name": "ESIGN",
                            "status": "TRIALING",
                            "start_date": "2026-02-05T00:00:00Z",
                            "trial_end": "2026-03-05T00:00:00Z",
                        }
                    },
                    response_only=True
                ),
                OpenApiExample(
                    "Successful Paid Subscription (Pending Payment)",
                    value={
                        "detail": "Subscription created successfully",
                        "subscription": {
                            "id": "123e4567-e89b-12d3-a456-426614174001",
                            "profile_id": "123e4567-e89b-12d3-a456-426614174001",
                            "setup_intent_id": "seti_1234567890",
                            "plan_name": "ESIGN",  
                            "status": "UNPAID",
                        }
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid request or validation error",
            examples=[
                OpenApiExample(
                    "Invalid Plan",
                    value={"detail": "Plan name is invalid"},
                    response_only=True
                ),
                OpenApiExample(
                    "Billing Interval Required",
                    value={"detail": "Billing interval is required for paid subscriptions"},
                    response_only=True
                )
            ]
        ),
        403: OpenApiResponse(
            description="Trial eligibility or subscription rule violation",
            examples=[
                OpenApiExample(
                    "Trial Not Allowed",
                    value={"detail": "User is not eligible for trial"},
                    response_only=True
                )
            ]
        ),
        404: OpenApiResponse(
            description="Profile not found",
            examples=[
                OpenApiExample(
                    "Profile Not Found",
                    value={"detail": "Profile not found"},
                    response_only=True
                )
            ]
        )
    },
    examples=[
        OpenApiExample(
            "Create Trial Subscription",
            value={
                "profile_id": "123e4567-e89b-12d3-a456-426614174001",
                "plan_name": "ESIGN",
                "status": "TRIALING",
                "start_date": "2026-02-05T00:00:00Z",
                "trial_end": "2026-03-05T00:00:00Z",
            },
            request_only=True
        ),

        OpenApiExample(
            "Create Paid Subscription (Pending Payment)",
            value={
                "profile_id": "123e4567-e89b-12d3-a456-426614174001",
                "setup_intent_id": "seti_1234567890",
                "plan_name": "ESIGN",  
                "status": "UNPAID",
            },
            request_only=True
        )
    ],
    tags=["Subscription Management"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def create_subscription_view(request):
    """User initial Subscription & licensing Creation Endpoint"""
    
    serializer = SubscriptionRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Get profile_id
    profile_id = data['profile_id']
    
    # Get Profile
    try:
        profile = Profile.objects.get(id=profile_id)

    
    except Profile.DoesNotExist:
        return Response(
            {"detail": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    setup_intent_id = data.get('setup_intent_id')
    if setup_intent_id:
        profile.setup_intent_id = setup_intent_id
        profile.save()
    
    # Normalize plan name
    try:
        plan_name = normalize_plan_name(data['plan_name'])
    except ValueError as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get subscription status from request (default to TRIALING)
    subscription_status = normalize_subscription_status(data.get('status'))
    
    # If user is signing up for a trial, check if they're eligible
    if subscription_status == SubscriptionStatus.TRIALING:
        can_trial, error_message = can_start_trial(profile, plan_name)
        if not can_trial:
            return Response(
                {"detail": error_message},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Determine billing interval
    billing_interval = BillingInterval.NONE  # Default to NONE for trial subscriptions 


    
    
    # Prepare subscription data
    subscription_data = {
        'profile': profile,
        'plan_name': plan_name,
        'status': subscription_status,
        'billing_interval': billing_interval,
     
    }
    
    # Add optional fields if provided


    if data.get('no_of_licenses'):
        subscription_data['no_of_licenses'] = data['no_of_licenses']



    if data.get('trial_end'):
        subscription_data['trial_end'] = data['trial_end']
    
    if data.get('cancel_at'):
        subscription_data['cancel_at'] = data['cancel_at']
    
    if 'cancel_at_period_end' in data:
        subscription_data['cancel_at_period_end'] = data['cancel_at_period_end']
    
    if data.get('pending_billing_interval'):
        subscription_data['pending_billing_interval'] = data['pending_billing_interval']
    
    if data.get('pending_number_of_licenses'):
        subscription_data['pending_number_of_licenses'] = data['pending_number_of_licenses']

    # Deactivate existing active/trialing subscriptions
    Subscription.objects.filter(
        profile=profile,
        status__in=[
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            # SubscriptionStatus.PAST_DUE,  # optional based on your business logic
        ],
    ).update(
        status=SubscriptionStatus.CANCELED,
        cancel_at=timezone.now(),
        cancel_at_period_end=False,
    )
    
    # Create Subscription
    subscription = Subscription.objects.create(**subscription_data)
    
    # Assign license to the newly created user
    try:
        first_user = profile.first_user()
        if first_user:
            LicenseService.assign_license(first_user)
            logger.info(f"License assigned to user {first_user.email}")
    except Exception as e:
        # Log the error but don't fail registration
        # User is created but without a license - admin can assign later
        logger.warning(f"Failed to assign license: {str(e)}")
        print(f"Failed to assign license: {str(e)}")
    
    # Prepare response data
    
    
    response_data = {
        'detail': 'Subscription created successfully',
        'subscription': {
            'id': str(subscription.id),
            'profile_id': str(subscription.profile.id),
            'plan_name': subscription.plan_name,
            'status': subscription.status,
            'no_of_licenses': subscription.no_of_licenses,
        }
    }
    
    # Add optional fields to response if they exist

    
    if subscription.trial_end:
        response_data['subscription']['trial_end'] = subscription.trial_end.isoformat()
    
 
    return Response(response_data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Update Subscription (Admin Only)",
    description="""
    Update subscription or profile details. Admin only endpoint.
    Allows administrators to update subscription and profile details.
    Useful for customer support and manual subscription management.
    
    **Authentication:** Bearer token required (Admin only)
    
    **Headers:**
    - `Authorization`: Bearer <access_token>
    
    **Request Body:**
    - `profile_id` (string, required): UUID of the profile to update
    - `plan_name` (string, optional): FREE_ESIGN, ESIGN, or EDMS_PLUS
    - `status` (string, optional): Subscription status (incomplete, trialing, active, past_due, canceled, unpaid)
    - `no_of_licenses` (integer, optional): Number of licenses
    - `billing_interval` (string, optional): MONTHLY or YEARLY
    - `profile_name` (string, optional): New profile name
    - `org_name` (string, optional): New organization name (for organizations only)
    
    **Response:**
    - `detail` (string): Success message
    - `profile` (object): Updated profile information
    - `subscription` (object): Updated subscription information
    """,
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'profile_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'UUID of the profile to update',
                    'example': '123e4567-e89b-12d3-a456-426614174001'
                },
                'plan_name': {
                    'type': 'string',
                    'enum': ['FREE_ESIGN', 'ESIGN', 'EDMS_PLUS'],
                    'description': 'Subscription plan',
                    'nullable': True
                },
                'status': {
                    'type': 'string',
                    'enum': ['incomplete', 'incomplete_expired', 'trialing', 'active', 'past_due', 'canceled', 'unpaid'],
                    'description': 'Subscription status',
                    'nullable': True
                },
                'no_of_licenses': {
                    'type': 'integer',
                    'description': 'Number of licenses',
                    'example': 5,
                    'nullable': True
                },
                'billing_interval': {
                    'type': 'string',
                    'enum': ['MONTHLY', 'YEARLY'],
                    'description': 'Billing interval',
                    'nullable': True
                },
                'profile_name': {
                    'type': 'string',
                    'description': 'New profile name',
                    'example': 'Updated Company Name',
                    'nullable': True
                },
                'org_name': {
                    'type': 'string',
                    'description': 'New organization name (for organizations only)',
                    'example': 'Acme Corporation',
                    'nullable': True
                }
            },
            'required': ['profile_id']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Subscription updated successfully",
            examples=[
                OpenApiExample(
                    'Update Success',
                    value={
                        'detail': 'Subscription updated successfully',
                        'profile': {
                            'id': '123e4567-e89b-12d3-a456-426614174001',
                            'name': 'Updated Company Name',
                            'type': 'ORGANIZATION',
                            'org_name': 'Acme Corporation'
                        },
                        'subscription': {
                            'plan_name': 'EDMS_PLUS',
                            'status': 'active',
                            'no_of_licenses': 10,
                            'billing_interval': 'YEARLY'
                        }
                    },
                    response_only=True,
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid input or profile_id missing",
            examples=[
                OpenApiExample(
                    'Missing Profile ID',
                    value={'detail': 'profile_id is required'},
                    response_only=True,
                ),
                OpenApiExample(
                    'Invalid Plan',
                    value={'detail': 'Invalid plan_name: INVALID_PLAN'},
                    response_only=True,
                )
            ]
        ),
        403: OpenApiResponse(description="User is not an admin"),
        404: OpenApiResponse(
            description="Profile or subscription not found",
            examples=[
                OpenApiExample(
                    'Profile Not Found',
                    value={'detail': 'Profile not found'},
                    response_only=True,
                )
            ]
        ),
    },
    examples=[
        OpenApiExample(
            'Update Plan and Licenses',
            value={
                'profile_id': '123e4567-e89b-12d3-a456-426614174001',
                'plan_name': 'EDMS_PLUS',
                'no_of_licenses': 10
            },
            request_only=True,
        ),
        OpenApiExample(
            'Update Status',
            value={
                'profile_id': '123e4567-e89b-12d3-a456-426614174001',
                'status': 'active'
            },
            request_only=True,
        ),
        OpenApiExample(
            'Update Profile Info',
            value={
                'profile_id': '123e4567-e89b-12d3-a456-426614174001',
                'profile_name': 'New Company Name',
                'org_name': 'New Organization LLC'
            },
            request_only=True,
        ),
    ],
    tags=['Subscription Management']
)
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
@transaction.atomic
def update_subscription_view(request):
    """Subscription Update Endpoint (Admin Only)"""
    profile_id = request.data.get("profile_id")
    if not profile_id:
        return Response({"detail": "profile_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        profile = Profile.objects.get(id=profile_id)
        subscription = profile.subscriptions.filter(
            status__in=[
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
                SubscriptionStatus.PAST_DUE,  # optional
            ]
        ).first()
    except Profile.DoesNotExist:
        return Response({"detail": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
    except Subscription.DoesNotExist:
        return Response({"detail": "Subscription not found for this profile"}, status=status.HTTP_404_NOT_FOUND)

    # Update profile fields if present
    profile_name = request.data.get("profile_name")
    org_name = request.data.get("org_name")
    if profile_name:
        profile.name = profile_name
    if org_name and profile.type == "ORGANIZATION":
        profile.org_name = org_name
    profile.save()

    # Update subscription fields if present
    plan_name = request.data.get("plan_name")
    if plan_name:
        try:
            subscription.plan_name = plan_name.upper()
        except ValueError:
            return Response({"detail": f"Invalid plan_name: {plan_name}"}, status=status.HTTP_400_BAD_REQUEST)

    status_val = request.data.get("status")
    if status_val and status_val.upper() in SubscriptionStatus.values:
        subscription.status = status_val.upper()

    no_of_licenses = request.data.get("no_of_licenses")
    if no_of_licenses is not None:
        try:
            subscription.no_of_licenses = int(no_of_licenses)
        except ValueError:
            return Response({"detail": "no_of_licenses must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

    billing_interval = request.data.get("billing_interval")
    if billing_interval and billing_interval.upper() in BillingInterval.values:
        subscription.billing_interval = billing_interval.upper()
    
    if profile.type == UserType.INDIVIDUAL:
        subscription.no_of_licenses = 1

    subscription.save()

    return Response({
        "detail": "Subscription updated successfully",
        "profile": {
            "id": str(profile.id),
            "name": profile.name,
            "type": profile.type,
            "org_name": profile.org_name,
        },
        "subscription": {
            "plan_name": subscription.plan_name,
            "status": subscription.status,
            "no_of_licenses": subscription.no_of_licenses,
            "billing_interval": subscription.billing_interval,
        }
    }, status=status.HTTP_200_OK)

@extend_schema(
    summary="Update Trial Billing Preferences (Stripe Webhook)",
    description="""
Stripe can update a user's trial subscription preferences (billing interval, number of licenses)
before the trial is activated.

No login required — this endpoint is meant for Stripe webhook calls.

**Request Body:**
- `pending_billing_interval` (string, optional): MONTHLY or YEARLY
- `pending_number_of_licenses` (integer, optional): Number of licenses to assign

**Response:**
- `subscription_id` (string): UUID of the subscription
- `plan_name` (string): Current plan
- `status` (string): Subscription status
- `trial_end` (string): Trial end datetime
- `pending_billing_interval` (string): Updated pending billing interval
- `pending_number_of_licenses` (integer): Updated pending license count
- `stripe_subscription_id` (string|null): Associated Stripe subscription ID
""",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'pending_billing_interval': {
                    'type': 'string',
                    'enum': ['MONTHLY', 'YEARLY'],
                    'nullable': True,
                    'description': 'Preferred billing interval'
                },
                'pending_number_of_licenses': {
                    'type': 'integer',
                    'nullable': True,
                    'description': 'Preferred number of licenses'
                }
            }
        }
    },
    responses={
        200: {
            'description': 'Subscription preferences updated successfully'
        },
        404: {
            'description': 'Subscription not found'
        },
        400: {
            'description': 'Invalid payload'
        }
    },
    tags=['Subscription Management']
)
@api_view(['PATCH'])
@transaction.atomic
def update_trial_billing_preferences_stripe(request, subscription_id):
    """
    Update pending trial billing preferences via Stripe webhook.
    No login required.
    """

    try:
        subscription = Subscription.objects.get(
            id=subscription_id,
            profile=request.user.profile
        )
    except Subscription.DoesNotExist:
        return Response(
            {"detail": "Subscription not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    # Optional: verify Stripe signature here

    pending_interval = request.data.get("pending_billing_interval")
    if pending_interval and pending_interval.upper() in ['MONTHLY', 'YEARLY']:
        subscription.pending_billing_interval = pending_interval.upper()

    pending_licenses = request.data.get("pending_number_of_licenses")
    if pending_licenses is not None:
        try:
            subscription.pending_number_of_licenses = int(pending_licenses)
        except ValueError:
            return Response({"detail": "pending_number_of_licenses must be an integer"},
                            status=status.HTTP_400_BAD_REQUEST)

    subscription.save()

    return Response({
        "subscription_id": str(subscription.id),
        "plan_name": subscription.plan_name,
        "status": subscription.status,
        "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
        "pending_billing_interval": subscription.pending_billing_interval,
        "pending_number_of_licenses": subscription.pending_number_of_licenses,
        "stripe_subscription_id": subscription.stripe_subscription_id,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="List Subscription Events",
    description="""
Retrieve all events for a specific subscription.

**Authentication:** Bearer token required

The identifier can be either:
- Stripe subscription ID (e.g., `sub_ABC123`)
- Internal subscription UUID (e.g., `123e4567-e89b-12d3-a456-426614174001`)
""",
    parameters=[
        OpenApiParameter(
            name="identifier",
            description="Stripe subscription ID or Subscription UUID",
            required=True,
            type=str,
            location=OpenApiParameter.PATH,
            examples=[
                OpenApiExample(
                    "Stripe Subscription ID",
                    value="sub_ABC123"
                ),
                OpenApiExample(
                    "Internal Subscription UUID",
                    value="123e4567-e89b-12d3-a456-426614174001"
                ),
            ],
        )
    ],
    responses={
        200: OpenApiResponse(
            description="List of subscription events",
            examples=[
                OpenApiExample(
                    "Successful Response",
                    value={
                        "subscription_id": "123e4567-e89b-12d3-a456-426614174001",
                        "stripe_subscription_id": "sub_ABC123",
                        "events": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "event_type": "activated",
                                "plan_name": "EDMS_PLUS",
                                "status": "active",
                                "billing_interval": "MONTHLY",
                                "no_of_licenses": 3,
                                "previous_plan_name": "ESIGN",
                                "previous_status": "trialing",
                                "previous_billing_interval": "MONTHLY",
                                "previous_no_of_licenses": 1,
                                "metadata": {
                                    "source": "stripe_sync_webhook",
                                    "stripe_subscription_id": "sub_ABC123"
                                },
                                "created_at": "2026-02-20T10:30:00Z"
                            },
                            {
                                "id": "660e8400-e29b-41d4-a716-446655440001",
                                "event_type": "payment_failed",
                                "plan_name": "EDMS_PLUS",
                                "status": "past_due",
                                "billing_interval": "MONTHLY",
                                "no_of_licenses": 3,
                                "previous_plan_name": "EDMS_PLUS",
                                "previous_status": "active",
                                "previous_billing_interval": "MONTHLY",
                                "previous_no_of_licenses": 3,
                                "metadata": {
                                    "source": "stripe_sync_webhook",
                                    "stripe_subscription_id": "sub_ABC123"
                                },
                                "created_at": "2026-03-01T08:15:00Z"
                            }
                        ]
                    },
                    response_only=True
                )
            ]
        ),
        403: OpenApiResponse(description="Not authorized to access this subscription"),
        404: OpenApiResponse(description="Subscription not found"),
    },
    tags=["Subscription Management"]
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_subscription_events(request, identifier):
    """
    Returns all subscription events for a given subscription.
    Identifier can be stripe_subscription_id or internal UUID.
    """
    identifier = identifier.strip()  # remove leading/trailing whitespace

    subscription = None

    # First, try to find by stripe_subscription_id
    subscription = Subscription.objects.filter(stripe_subscription_id=identifier).first()

    # If not found, try UUID
    if subscription is None:
        try:
            uid = uuid.UUID(identifier)  # validate UUID
            subscription = Subscription.objects.filter(id=uid).first()
        except ValueError:
            # Invalid UUID format, cannot search by internal id
            subscription = None

    if not subscription:
        return Response(
            {"detail": "Subscription not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # 🔒 Ensure user belongs to this profile, except superadmins
    if not request.user.is_superuser and subscription.profile != request.user.profile:
        return Response(
            {"detail": "You are not authorized to access this subscription"},
            status=status.HTTP_403_FORBIDDEN
        )

    events = subscription.events.all()

    response_data = []
    for event in events:
        response_data.append({
            "id": str(event.id),
            "event_type": event.event_type,
            "plan_name": event.plan_name,
            "status": event.status,
            "billing_interval": event.billing_interval,
            "no_of_licenses": event.no_of_licenses,
            "previous_plan_name": event.previous_plan_name,
            "previous_status": event.previous_status,
            "previous_billing_interval": event.previous_billing_interval,
            "previous_no_of_licenses": event.previous_no_of_licenses,
            "metadata": event.metadata,
            "created_at": event.created_at.isoformat(),
        })

    return Response(
        {
            "subscription_id": str(subscription.id),
            "stripe_subscription_id": subscription.stripe_subscription_id,
            "events": response_data
        },
        status=status.HTTP_200_OK
    )

@extend_schema(
    summary="Get Subscriptions by Profile",
    description="""
Retrieve all subscriptions associated with a specific profile.

**Authentication:** Authenticated endpoint  

**Path Parameter:**
- `profile_id` (uuid, required): Profile UUID to fetch subscriptions for  

**Response:**
- `profile_id`: The requested profile UUID  
- `subscriptions`: List of subscription objects with key details:
    - `subscription_id`: UUID of the subscription
    - `plan_name`: Plan name
    - `status`: Current subscription status
    - `stripe_subscription_id`: Stripe subscription ID
    - `billing_interval`: Billing interval (MONTHLY, YEARLY, NONE)
    - `no_of_licenses`: Number of licenses
    - `current_period_end`: End of current billing or trial period
    - `trial_end`: Trial end date (if any)
""",
    responses={
        200: OpenApiResponse(
            description="Subscriptions fetched successfully",
            examples=[
                OpenApiExample(
                    "Profile Subscriptions",
                    value={
                        "profile_id": "550e8400-e29b-41d4-a716-446655440000",
                        "subscriptions": [
                            {
                                "subscription_id": "sub_uuid_456",
                                "plan_name": "ESIGN",
                                "status": "ACTIVE",
                                "stripe_subscription_id": "sub_1234567890",
                                "billing_interval": "MONTHLY",
                                "no_of_licenses": 1,
                                "current_period_end": "2026-03-09T10:30:00Z",
                                "trial_end": None
                            }
                        ]
                    },
                    response_only=True
                )
            ]
        ),
        404: OpenApiResponse(description="Profile not found")
    },
    tags=["Subscription Management"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscriptions_by_profile(request, profile_id):
    """Get all subscriptions for a given profile."""
    try:
        profile = Profile.objects.get(id=profile_id)
    except Profile.DoesNotExist:
        return Response({"detail": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

    subscriptions = Subscription.objects.filter(profile=profile)
    subscription_list = []

    for sub in subscriptions:
        subscription_list.append({
            "subscription_id": str(sub.id),
            "plan_name": sub.plan_name,
            "status": sub.status,
            "stripe_subscription_id": sub.stripe_subscription_id,
            "billing_interval": sub.billing_interval,
            "no_of_licenses": sub.no_of_licenses,
            "current_period_end": sub.current_period_end.isoformat() if hasattr(sub, 'current_period_end') and sub.current_period_end else None,
            "trial_end": sub.trial_end.isoformat() if sub.trial_end else None
        })

    return Response({
        "profile_id": str(profile.id),
        "subscriptions": subscription_list
    }, status=status.HTTP_200_OK)

@extend_schema(
    summary="Sync/Update Subscription via Stripe",
    description="""
Update a subscription using either the Stripe subscription ID or the internal subscription UUID.

**Authentication:** None required (public endpoint)



**Request Body:**
- `stripe_subscription_id` (string, required): Stripe subscription ID
- `subscription_id` (string, required): Subscription ID - UUID
- Optional fields to update:
    - `plan_name` (string): Subscription plan name
    - `status` (string): Subscription status
    - `billing_interval` (string): Billing interval (MONTHLY, YEARLY, NONE)
    - `no_of_licenses` (integer): Number of licenses
    - `pending_number_of_licenses` (integer): Pending license change
    - `pending_billing_interval` (string): Pending billing interval
    - `start_date` (datetime): Subscription start date
    - `trial_end` (datetime): Trial end date
    - `cancel_at` (datetime): Scheduled cancellation date
    - `cancel_at_period_end` (boolean): Cancel at period end



---

### Allowed Billing Interval Values
- `MONTHLY`
- `YEARLY`


---


### Allowed Plan_name Values
- `FREE_ESIGN`
- `ESIGN`
- `EDMS_PLUS`


---

### Allowed Status Values
- `INCOMPLETE`
- `INCOMPLETE_EXPIRED`
- `TRIALING`
- `ACTIVE`
- `PAST_DUE`
- `CANCELED`
- `UNPAID`
""",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "stripe_subscription_id": {"type": "string", "description": "Stripe subscription ID"},
                "subscription_id": {"type": "string", "description": "Subscription ID - UUID"},
                "plan_name": {"type": "string", "description": "Subscription plan name"},
                "status": {"type": "string", "description": "Subscription status"},
                "billing_interval": {"type": "string", "description": "Billing interval"},
                "no_of_licenses": {"type": "integer", "description": "Number of licenses"},
                "pending_number_of_licenses": {"type": "integer", "description": "Pending license change"},
                "pending_billing_interval": {"type": "string", "description": "Pending billing interval"},
                "start_date": {"type": "string", "format": "date-time", "description": "Subscription start date"},
                "trial_end": {"type": "string", "format": "date-time", "description": "Trial end date"},
                "cancel_at": {"type": "string", "format": "date-time", "description": "Scheduled cancellation date"},
                "cancel_at_period_end": {"type": "boolean", "description": "Cancel at period end"}
            },
            "required": ["stripe_subscription_id"]
        }
    },
    responses={
        200: OpenApiResponse(
            description="Subscription updated successfully",
            examples=[
                OpenApiExample(
                    "Updated Subscription",
                    value={
                        "detail": "Subscription updated successfully",
                        "subscription": {
                            "id": "123e4567-e89b-12d3-a456-426614174001",
                            "stripe_subscription_id": "sub_ABC123",
                            "profile_id": "550e8400-e29b-41d4-a716-446655440000",
                            "plan_name": "EDMS_PLUS",
                            "status": "ACTIVE",
                            "billing_interval": "MONTHLY",
                            "no_of_licenses": 3,
                            "pending_number_of_licenses": None,
                            "pending_billing_interval": None,
                            "start_date": "2026-02-09T10:30:00Z",
                            "trial_end": None,
                            "cancel_at": None,
                            "cancel_at_period_end": False
                        }
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(description="Invalid request or missing stripe_subscription_id"),
        404: OpenApiResponse(description="Subscription not found")
    },
    tags=["Subscription Management"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def stripe_sync_subscription_webhook(request):
    """Update subscription fields dynamically using stripe_subscription_id"""
    serializer = SubscriptionRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    stripe_sub_id = data.get("stripe_subscription_id")
    subscription_id = data.get("subscription_id")

    if not stripe_sub_id and not subscription_id:
        return Response(
            {"detail": "stripe_subscription_id or subscription_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    subscription = None

    if stripe_sub_id:
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
        except Subscription.DoesNotExist:
            pass

    if subscription is None:
        if not subscription_id:
            return Response({"detail": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            subscription = Subscription.objects.get(id=subscription_id)
        except Subscription.DoesNotExist:
            return Response({"detail": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)

    # Fields that can be updated
    updatable_fields = [
        "plan_name", "status", "billing_interval",
        "no_of_licenses", "pending_number_of_licenses", "pending_billing_interval",
        "start_date", "trial_end", "cancel_at", "cancel_at_period_end"
    ]
    for field in updatable_fields:
        if field in data and data[field] is not None:
            setattr(subscription, field, data[field])

    # Normalize plan_name and status if provided
    if "plan_name" in data and data["plan_name"]:
        try:
            subscription.plan_name = normalize_plan_name(data["plan_name"])
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    if "status" in data and data["status"]:
        subscription.status = normalize_subscription_status(data["status"])

    subscription.save()

    # Capture previous state BEFORE making changes
    previous_values = {
        "plan_name": subscription.plan_name,
        "status": subscription.status,
        "billing_interval": subscription.billing_interval,
        "no_of_licenses": subscription.no_of_licenses,
    }
    event_type = determine_subscription_event(subscription, previous_values)

    SubscriptionEvent.objects.create(
        subscription=subscription,
        event_type=event_type,
        # Current state snapshot
        plan_name=subscription.plan_name,
        status=subscription.status,
        billing_interval=subscription.billing_interval,
        no_of_licenses=subscription.no_of_licenses,
        # Previous state
        previous_plan_name=previous_values["plan_name"],
        previous_status=previous_values["status"],
        previous_billing_interval=previous_values["billing_interval"],
        previous_no_of_licenses=previous_values["no_of_licenses"],
        # Extra context
        metadata={
            "source": "stripe_sync_webhook",
            "stripe_subscription_id": stripe_sub_id,
        }
    )

    # Optionally assign license
    try:
        first_user = subscription.profile.first_user()
        if first_user:
            LicenseService.assign_license(first_user)
    except Exception as e:
        logger.warning(f"Failed to assign license: {str(e)}")

    # Build dynamic response
    response_data = {
        "detail": "Subscription updated successfully",
        "subscription": {
            "id": str(subscription.id),
            "stripe_subscription_id": subscription.stripe_subscription_id,
            "profile_id": str(subscription.profile.id)
        }
    }
    for field in updatable_fields:
        value = getattr(subscription, field)
        if value is not None:
            if isinstance(value, (datetime.datetime, datetime.date)):
                response_data["subscription"][field] = value.isoformat()
            else:
                response_data["subscription"][field] = value

    return Response(response_data, status=status.HTTP_200_OK)





# ============================================================================
# SECTION 4: TRIAL MANAGEMENT VIEWS (Authenticated Users)
# ============================================================================

@extend_schema(
    summary="Check Trial Eligibility",
    description="""
    Check which plans are eligible for trial for the authenticated user.
    Useful for showing users their trial options before registration or upgrade.
    
    **Authentication:** Bearer token required
    
    **Headers:**
    - `Authorization`: Bearer <access_token>
    
    **Response:**
    Returns eligibility status for all three plan types:
    
    - **FREE_ESIGN:** Always available (free for life, no trial)
    - **ESIGN:** Trial eligibility based on history
    - **EDMS_PLUS:** Trial eligibility based on history
    
    Each plan includes:
    - `can_trial` (boolean): Whether user can start a trial
    - `reason` (string): Explanation of eligibility status
    - `has_trialed` (boolean): Whether user has previously trialed this plan
    - `is_free` (boolean): Whether the plan is free
    - `note` (string, optional): Additional information
    
    **Trial Rules Summary:**
    1. FREE_ESIGN: No trial (it's free forever)
    2. ESIGN: Can trial if never trialed ESIGN or EDMS_PLUS
    3. EDMS_PLUS: Can trial if never trialed EDMS_PLUS (even after ESIGN trial)
    """,
    request=None,
    responses={
        200: OpenApiResponse(
            description="Trial eligibility information",
            examples=[
                OpenApiExample(
                    'New User - All Trials Available',
                    value={
                        'FREE_ESIGN': {
                            'can_trial': False,
                            'reason': 'No trial needed - FREE_ESIGN is free for life',
                            'is_free': True
                        },
                        'ESIGN': {
                            'can_trial': True,
                            'reason': 'Available for trial',
                            'has_trialed': False,
                            'is_free': False
                        },
                        'EDMS_PLUS': {
                            'can_trial': True,
                            'reason': 'Available for trial',
                            'has_trialed': False,
                            'is_free': False,
                            'note': None
                        }
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    'After ESIGN Trial - EDMS_PLUS Still Available',
                    value={
                        'FREE_ESIGN': {
                            'can_trial': False,
                            'reason': 'No trial needed - FREE_ESIGN is free for life',
                            'is_free': True
                        },
                        'ESIGN': {
                            'can_trial': False,
                            'reason': 'Already trialed eSign',
                            'has_trialed': True,
                            'is_free': False
                        },
                        'EDMS_PLUS': {
                            'can_trial': True,
                            'reason': 'Available for trial',
                            'has_trialed': False,
                            'is_free': False,
                            'note': 'Can trial even after eSign trial'
                        }
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    'After EDMS_PLUS Trial - No ESIGN Trial',
                    value={
                        'FREE_ESIGN': {
                            'can_trial': False,
                            'reason': 'No trial needed - FREE_ESIGN is free for life',
                            'is_free': True
                        },
                        'ESIGN': {
                            'can_trial': False,
                            'reason': 'Already trialed EDMS+',
                            'has_trialed': False,
                            'is_free': False
                        },
                        'EDMS_PLUS': {
                            'can_trial': False,
                            'reason': 'Already trialed EDMS+',
                            'has_trialed': True,
                            'is_free': False,
                            'note': None
                        }
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    'All Trials Used',
                    value={
                        'FREE_ESIGN': {
                            'can_trial': False,
                            'reason': 'No trial needed - FREE_ESIGN is free for life',
                            'is_free': True
                        },
                        'ESIGN': {
                            'can_trial': False,
                            'reason': 'Already trialed eSign',
                            'has_trialed': True,
                            'is_free': False
                        },
                        'EDMS_PLUS': {
                            'can_trial': False,
                            'reason': 'Already trialed EDMS+',
                            'has_trialed': True,
                            'is_free': False,
                            'note': None
                        }
                    },
                    response_only=True,
                )
            ]
        ),
        401: OpenApiResponse(description="Invalid or missing token"),
    },
    tags=['Trial Management']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trial_eligibility_view(request):
    """
    Trial Eligibility Check Endpoint
    
    Returns detailed information about which plans the user can trial.
    
    Headers:
        - Authorization: Bearer <access_token>
    
    Returns:
        - Eligibility information for all three plan types
        - Reasons for eligibility or ineligibility
        - Trial history flags
    
    Status Codes:
        200: Success - returns eligibility information
        401: Authentication failed
    """
    from .authentication import JWTAuthentication
    from .utils import get_trial_eligibility
    
    auth = JWTAuthentication()
    auth_result = auth.authenticate(request)
    if not auth_result:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    current_user = auth_result[0]
    profile = current_user.profile

    eligibility = get_trial_eligibility(profile)
    
    return Response(eligibility, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get Trial Status",
    description="""
    Get current trial status including days remaining and conversion eligibility.
    
    **Authentication:** Bearer token required
    
    **Headers:**
    - `Authorization`: Bearer <access_token>
    
    **Response (if on trial):**
    - `is_trial` (boolean): true
    - `plan_name` (string): Name of the plan being trialed
    - `trial_start` (datetime): When the trial started
    - `trial_end` (datetime): When the trial is scheduled to end
    - `days_remaining` (integer): Days left in trial
    - `hours_remaining` (integer): Hours left in trial
    - `has_expired` (boolean): Whether trial has expired
    - `can_convert` (boolean): Whether trial can be converted
    
    **Response (if not on trial):**
    - `is_trial` (boolean): false
    - `message` (string): "No active trial found"
    """,
    request=None,
    responses={
        200: OpenApiResponse(
            description="Trial status retrieved",
            examples=[
                OpenApiExample(
                    'Active Trial',
                    value={
                        'is_trial': True,
                        'plan_name': 'ESIGN',
                        'trial_start': '2026-01-21T10:00:00Z',
                        'trial_end': '2026-02-04T10:00:00Z',
                        'days_remaining': 14,
                        'hours_remaining': 336,
                        'has_expired': False,
                        'can_convert': True
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    'No Active Trial',
                    value={
                        'is_trial': False,
                        'message': 'No active trial found'
                    },
                    response_only=True,
                )
            ]
        ),
        401: OpenApiResponse(description="Invalid or missing token"),
    },
    tags=['Trial Management']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trial_status_view(request):
    """Trial Status Check Endpoint"""
    auth = JWTAuthentication()
    auth_result = auth.authenticate(request)
    if not auth_result:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    current_user = auth_result[0]
    profile = current_user.profile

    trial_status = get_trial_status(profile)
    
    if trial_status:
        return Response(trial_status, status=status.HTTP_200_OK)
    else:
        return Response({
            'is_trial': False,
            'message': 'No active trial found'
        }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get Trial History",
    description="""
    Get complete trial history for the authenticated user.
    
    **Authentication:** Bearer token required
    
    **Headers:**
    - `Authorization`: Bearer <access_token>
    
    **Response:**
    - `trial_history` (array): Array of trial records
      - `plan_name` (string): Plan that was trialed
      - `started_at` (datetime): Trial start date
      - `scheduled_end` (datetime): Originally scheduled end date (14 days)
      - `actual_end` (datetime): Actual end date (may be earlier if converted)
      - `converted` (boolean): Whether converted to paid
      - `conversion_date` (datetime): When conversion occurred
      - `early_conversion` (boolean): Whether converted early
      - `days_used` (integer): Number of days trial was active
    - `count` (integer): Total number of trials
    """,
    request=None,
    responses={
        200: OpenApiResponse(
            description="Trial history retrieved",
            examples=[
                OpenApiExample(
                    'Trial History',
                    value={
                        'trial_history': [
                            {
                                'plan_name': 'ESIGN',
                                'started_at': '2025-12-01T10:00:00Z',
                                'scheduled_end': '2025-12-15T10:00:00Z',
                                'actual_end': '2025-12-10T15:30:00Z',
                                'converted': True,
                                'conversion_date': '2025-12-10T15:30:00Z',
                                'early_conversion': True,
                                'days_used': 9
                            }
                        ],
                        'count': 1
                    },
                    response_only=True,
                )
            ]
        ),
        401: OpenApiResponse(description="Invalid or missing token"),
    },
    tags=['Trial Management']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trial_history_view(request):
    """Trial History Endpoint"""
    auth = JWTAuthentication()
    auth_result = auth.authenticate(request)
    if not auth_result:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    current_user = auth_result[0]
    profile = current_user.profile

    history = get_trial_history(profile)
    
    return Response({
        'trial_history': history,
        'count': len(history)
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Convert Trial to Paid Subscription",
    description="""
    Convert an active trial subscription to a paid/active subscription.
    This endpoint should be called after successful payment processing.
    
    **Authentication:** Bearer token required
    
    **Features:**
    - Supports early conversion (before 14 days)
    - Tracks conversion date and early conversion flag
    - Sets next billing period to 30 days from conversion
    - Updates trial history with conversion details
    
    **Requirements:**
    - User must have an active trial subscription
    - Can be called anytime during trial period
    
    **Headers:**
    - `Authorization`: Bearer <access_token>
    
    **Request Body (optional):**
    - `plan_name` (string, optional): Override plan name if different from current subscription
    
    **Response:**
    - `detail` (string): Success message with conversion type
    - `subscription` (object): Updated subscription details
      - `plan_name` (string): Active plan name
      - `status` (string): "active"
      - `no_of_licenses` (integer): Number of licenses
      - `billing_interval` (string): MONTHLY or YEARLY
      - `current_period_end` (datetime): Next billing date
    """,
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'plan_name': {
                    'type': 'string',
                    'enum': ['FREE_ESIGN', 'ESIGN', 'EDMS_PLUS'],
                    'description': 'Override plan name (optional)',
                    'nullable': True
                }
            }
        }
    },
    responses={
        200: OpenApiResponse(
            description="Trial converted successfully",
            examples=[
                OpenApiExample(
                    'Early Conversion',
                    value={
                        'detail': 'Trial converted to active subscription early (after 5 days)',
                        'subscription': {
                            'plan_name': 'ESIGN',
                            'status': 'active',
                            'no_of_licenses': 1,
                            'billing_interval': 'MONTHLY',
                            'current_period_end': '2026-02-20T12:00:00Z'
                        }
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    'Upgrade During Conversion',
                    value={
                        'detail': 'Trial converted to active subscription early (after 7 days)',
                        'subscription': {
                            'plan_name': 'EDMS_PLUS',
                            'status': 'active',
                            'no_of_licenses': 1,
                            'billing_interval': 'MONTHLY',
                            'current_period_end': '2026-02-20T12:00:00Z'
                        }
                    },
                    response_only=True,
                )
            ]
        ),
        400: OpenApiResponse(
            description="Subscription is not on trial",
            examples=[
                OpenApiExample(
                    'Not On Trial',
                    value={'detail': 'Subscription is not currently on trial'},
                    response_only=True,
                )
            ]
        ),
        401: OpenApiResponse(description="Invalid or missing token"),
    },
    examples=[
        OpenApiExample(
            'Convert Current Plan',
            value={},
            request_only=True,
        ),
        OpenApiExample(
            'Convert and Upgrade',
            value={
                'plan_name': 'EDMS_PLUS'
            },
            request_only=True,
        ),
    ],
    tags=['Trial Management']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def convert_trial_view(request):
    """Trial Conversion Endpoint"""
    auth = JWTAuthentication()
    auth_result = auth.authenticate(request)
    if not auth_result:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    current_user = auth_result[0]
    profile = current_user.profile
    
    plan_name = request.data.get('plan_name', None)

    success, message, subscription = convert_trial_to_active(profile, plan_name)
    
    if not success:
        return Response(
            {'detail': message},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({
        'detail': message,
        'subscription': {
            'plan_name': subscription.plan_name,
            'status': subscription.status,
            'no_of_licenses': subscription.no_of_licenses,
            'billing_interval': subscription.billing_interval,
            'current_period_end': subscription.current_period_end,
        }
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Cancel Trial",
    description="""
    Cancel an active trial without converting to a paid subscription.
    Sets subscription status to CANCELED and marks trial as ended.
    
    **Authentication:** Bearer token required
    
    **Headers:**
    - `Authorization`: Bearer <access_token>
    
    **Response:**
    - `detail` (string): Success message
    """,
    request=None,
    responses={
        200: OpenApiResponse(
            description="Trial cancelled successfully",
            examples=[
                OpenApiExample(
                    'Trial Cancelled',
                    value={'detail': 'Trial cancelled successfully'},
                    response_only=True,
                )
            ]
        ),
        400: OpenApiResponse(
            description="Subscription is not on trial",
            examples=[
                OpenApiExample(
                    'Not On Trial',
                    value={'detail': 'Subscription is not currently on trial'},
                    response_only=True,
                )
            ]
        ),
        401: OpenApiResponse(description="Invalid or missing token"),
    },
    tags=['Trial Management']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cancel_trial_view(request):
    """Trial Cancellation Endpoint"""
    auth = JWTAuthentication()
    auth_result = auth.authenticate(request)
    if not auth_result:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    current_user = auth_result[0]
    profile = current_user.profile

    success, message = cancel_trial(profile)
    
    if not success:
        return Response(
            {'detail': message},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({
        'detail': message
    }, status=status.HTTP_200_OK)



# ============================================================================
# SECTION 5: ORGANIZATION MANAGEMENT VIEWS (Admin Only)
# ============================================================================

@extend_schema(
    summary="Add organization user",
    description="""
Add a new user to an existing organization.

This endpoint allows an **organization admin** to create and attach a user
to their organization profile.

**Authentication**
- Bearer token required
- Admin users only

**Behavior**
- User is linked to the specified organization profile
- User inherits the organization's subscription
- User is created as a non-admin by default
- License availability should be validated before user creation
""",
    request=AddOrgUserRequestSerializer,
    responses={
        201: OpenApiResponse(
            response=RegisterResponseSerializer,
            description="User added successfully",
            examples=[
                OpenApiExample(
                    "User Added",
                    value={
                        "id": "123e4567-e89b-12d3-a456-426614174002",
                        "email": "newuser@acme.com",
                        "username": "newuser",
                        "first_name": "New",
                        "last_name": "User",
                        "plan_name": "EDMS_PLUS",
                        "is_domain_user": False,
                        "domain": None,
                        "profile_id": "123e4567-e89b-12d3-a456-426614174001",
                        "is_admin": False
                    },
                    response_only=True,
                )
            ],
        ),
        400: OpenApiResponse(
            description="Invalid input data"
        ),
        401: OpenApiResponse(
            description="Authentication credentials were not provided or are invalid"
        ),
        403: OpenApiResponse(
            description="User does not have admin privileges",
            examples=[
                OpenApiExample(
                    "Not Admin",
                    value={"detail": "Only admins can add users"},
                    response_only=True,
                )
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Add organization user",
            value={
                "email": "newuser@acme.com",
                "username": "newuser",
                "password": "SecurePass123!",
                "first_name": "New",
                "last_name": "User",
                "is_admin": False,
                "profile_id": "123e4567-e89b-12d3-a456-426614174001"
            },
            request_only=True,
        ),
    ],
    tags=["Organization Management"],
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def add_org_user_view(request):
    """
    Add organization user (Admin only)
    """

    # check if authenticated users account has an active subscription with available licenses before allowing to add user
    active_sub = request.user.profile.subscriptions.filter(
        status__in=[
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,  # optional depending on your logic
        ]
    ).first()

    # Check if there is an active subscription
    if not active_sub:
        return Response(
            {'detail': 'Your organization does not have an active subscription. Please contact your administrator.'},
            status=status.HTTP_403_FORBIDDEN
        )


    data = request.data
    
    # Normalize email / username
    email = data['email'].strip().lower()

    # Check if user with this email already exists
    if User.objects.filter(email=email).exists():
        existing_user = User.objects.get(email=email)
        
        # If user exists but hasn't verified email
        if not existing_user.is_active and not existing_user.email_verified:
            # Check if verification token has expired
            if existing_user.email_verification_token_expires and \
               existing_user.email_verification_token_expires < timezone.now():
                return Response(
                    {
                        "detail": "An account with this email exists but was not verified. Please use the resend verification endpoint to get a new verification link.",
                        "email": email,
                        "can_resend": True
                    },
                    status=status.HTTP_409_CONFLICT
                )
            else:
                return Response(
                    {
                        "detail": "An account with this email already exists but has not been verified. Please check your email for the verification link.",
                        "email": email,
                        "can_resend": True
                    },
                    status=status.HTTP_409_CONFLICT
                )
        else:
            # User exists and is verified/active
            return Response(
                {
                    "detail": "An account with this email already exists. Please login or use a different email address.",
                    "email": email
                },
                status=status.HTTP_409_CONFLICT
            )
    

    # ---- Permission check ----
    if not request.user.is_admin and not request.user.is_superuser:
        return Response(
            {'detail': 'Only admins can add users'},
            status=status.HTTP_403_FORBIDDEN
        )

    # ---- Fetch profile safely ----
    profile_id = data.get('profile_id')
    if not profile_id:
        return Response(
            {'detail': 'profile_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )


    try:
        profile = Profile.objects.get(id=profile_id)
    except Profile.DoesNotExist:
        return Response(
            {"detail": "Profile not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # ---- Ensure same organization (superuser exempt) ----
    if profile != request.user.profile and not request.user.is_superuser:
        return Response(
            {'detail': 'Can only add users to your organization'},
            status=status.HTTP_403_FORBIDDEN
        )

    # ---- Create user ----
    username = data.get('username', email.split('@')[0])  # Default to email prefix if username not provided
    try:
        # username=generate_unique_username(data['first_name'], data['last_name'])
        assigned = profile.users.filter(has_license=True, is_active=True).count()
       
        total_licenses = active_sub.no_of_licenses if active_sub else 0
        user = User.objects.create_user(
            email=data['email'],
            username=username,
            password=data['password'],
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            profile=profile,
            is_admin=data.get('is_admin', False),
            is_active=True,
            has_license=assigned < total_licenses,  # Assign license if available, else user will be created without license 
            license_assigned_at=timezone.now() if assigned < total_licenses else None
        )
    except KeyError as e:
        return Response(
            {'detail': f'Missing field: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

     # Assign license to the newly created user
    try:
        LicenseService.assign_license(user)
        logger.info(f"License assigned to user {user.email}")
    except Exception as e:
        # Log the error but don't fail registration
        # User is created but without a license - admin can assign later
        logger.warning(f"Failed to assign license to user {user.email}: {str(e)}")
        print(f"Failed to assign license to user {user.email}: {str(e)}")


   

    # ---- Response ----
    return Response(
        {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": user.is_admin,
            "profile_id": str(profile.id),
            "profile_type": profile.type,
            "message": "User added successfully"
        },
        status=status.HTTP_201_CREATED
    )



# ============================================================================
# SECTION 5: LICENSE MANAGEMENT VIEWS (Admin Only)
# ============================================================================

# ---- ASSIGN LICENSE ----
@extend_schema(
    summary="Assign a license to a user",
    description="Admin-only endpoint to assign a license to a user in the same profile",
    responses={
        200: {
            "description": "License assigned successfully",
            "examples": [{
                "message": "License assigned to user@example.com",
                "user_id": "uuid",
                "has_license": True
            }]
        },
        400: {"description": "Validation error"},
        403: {"description": "Forbidden: not admin or different profile"}
    },
    tags=["License Management"]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_license_view(request, user_id):
    if not request.user.is_admin:
        return Response({'detail': 'Only admins can assign licenses'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {"detail": "User not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if user.profile != request.user.profile and not request.user.is_superuser:
        return Response(
            {'detail': 'Can only manage licenses for users in your organization'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        LicenseService.assign_license(user)
        return Response({
            'message': f'License assigned to {user.email}',
            'user_id': str(user.id),
            'has_license': True
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---- REVOKE LICENSE ----
@extend_schema(
    summary="Revoke a license from a user",
    description="Admin-only endpoint to revoke a license from a user in the same profile. Cannot revoke own license.",
    responses={
        200: {
            "description": "License revoked successfully",
            "examples": [{
                "message": "License revoked from user@example.com",
                "user_id": "uuid",
                "has_license": False
            }]
        },
        400: {"description": "Validation error or trying to revoke own license"},
        403: {"description": "Forbidden: not admin or different profile"}
    },
    tags=["License Management"]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_license_view(request, user_id):
    if not request.user.is_admin:
        return Response({'detail': 'Only admins can revoke licenses'}, status=status.HTTP_403_FORBIDDEN)
    

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {"detail": "User not found."},
            status=status.HTTP_404_NOT_FOUND
        )
        
    if user.profile != request.user.profile and not request.user.is_superuser:
        return Response(
            {'detail': 'Can only manage licenses for users in your organization'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if user == request.user:
        return Response({'detail': 'Cannot revoke your own license'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        LicenseService.revoke_license(user)
        return Response({
            'message': f'License revoked from {user.email}',
            'user_id': str(user.id),
            'has_license': False
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---- LICENSE STATUS ----
@extend_schema(
    summary="Get license status for the profile",
    description="Retrieve subscription info and current license assignment status for all users in the profile",
    responses={
        200: {
            "description": "License status retrieved successfully",
            "examples": [{
                "total_licenses": 10,
                "assigned_licenses": 5,
                "available_licenses": 5,
                "subscription_status": "active",
                "users_with_licenses": [
                    {
                        "id": "uuid",
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "license_assigned_at": "2026-02-04T12:34:56Z"
                    }
                ]
            }]
        },
        404: {"description": "No subscription found"}
    },
    tags=["License Management"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def license_status_view(request):
    profile = request.user.profile
    subscription = profile.subscriptions.filter(
        status__in=[
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,  # optional based on your rules
        ]
    ).first()
    
    if not subscription:
        return Response({'detail': 'No subscription found'}, status=status.HTTP_404_NOT_FOUND)
    
    total_licenses = subscription.no_of_licenses
    assigned_licenses = LicenseService.get_assigned_licenses_count(profile)
    available_licenses = LicenseService.get_available_licenses(profile)
    
    users_with_licenses = profile.users.filter(
        has_license=True,
        is_active=True
    ).values('id', 'email', 'first_name', 'last_name', 'license_assigned_at')
    
    return Response({
        'total_licenses': total_licenses,
        'assigned_licenses': assigned_licenses,
        'available_licenses': available_licenses,
        'subscription_status': subscription.status,
        'users_with_licenses': list(users_with_licenses)
    }, status=status.HTTP_200_OK)



# ============================================================================
# SECTION 6: PROFILE AND SUBSCRIPTION UPDATE VIEWS (Public - No Auth)
# ============================================================================

@extend_schema(
    summary="Update Profile Stripe Customer ID",
    description="""
Update the stripe_customer_id for the currently authenticated user's profile.

**Authentication:** Required (Bearer token)

**Request Body:**
- `stripe_customer_id` (string, required): The Stripe customer ID to set

**Response:**
- Profile details with updated stripe_customer_id
""",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'stripe_customer_id': {
                    'type': 'string',
                    'description': 'Stripe customer ID'
                }
            },
            'required': ['stripe_customer_id']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Profile updated successfully",
            examples=[
                OpenApiExample(
                    "Success Response",
                    value={
                        "message": "Profile updated successfully",
                        "profile": {
                            "id": "123e4567-e89b-12d3-a456-426614174001",
                            "name": "John Doe",
                            "type": "INDIVIDUAL",
                            "stripe_customer_id": "cus_ABC123xyz",
                            "updated_at": "2026-02-05T10:30:00Z"
                        }
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(description="Invalid request data"),
        404: OpenApiResponse(description="Profile not found")
    },
    examples=[
        OpenApiExample(
            "Update Stripe Customer ID",
            value={
                "stripe_customer_id": "cus_ABC123xyz"
            },
            request_only=True
        )
    ],
    tags=["Profile Management"]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_profile_stripe_customer_view(request):
    """Update Profile Stripe Customer ID - Authenticated Endpoint"""
    
    user = request.user
    
    # Fetch the profile associated with the logged-in user
    try:
        profile = user.profile  # assumes OneToOneField: user.profile
    except Profile.DoesNotExist:
        return Response(
            {'detail': 'Profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    stripe_customer_id = request.data.get('stripe_customer_id')
    if not stripe_customer_id:
        return Response(
            {'detail': 'stripe_customer_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Update stripe_customer_id
    profile.stripe_customer_id = stripe_customer_id.strip()
    profile.save(update_fields=['stripe_customer_id', 'updated_at'])
    
    return Response(
        {
            'message': 'Profile updated successfully',
            'profile': {
                'id': str(profile.id),
                'name': profile.name,
                'type': profile.type,
                'stripe_customer_id': profile.stripe_customer_id,
                'updated_at': profile.updated_at.isoformat()
            }
        },
        status=status.HTTP_200_OK
    )

@extend_schema(
    summary="Get Stripe Setup Intent ID",
    description="""
Retrieve the Stripe Setup Intent ID for the currently authenticated user's profile.

**Authentication:** Required (Bearer token)

**Request:** No body required. The logged-in user is used to fetch the profile.

**Response:**  
- `message` (string): Success message  
- `profile` (object): Profile details including `setup_intent_id`
""",
    responses={
        200: OpenApiResponse(
            description="Successfully retrieved setup_intent_id",
            examples=[
                OpenApiExample(
                    "Success Response",
                    value={
                        "message": "Profile retrieved successfully",
                        "profile": {
                            "id": "123e4567-e89b-12d3-a456-426614174001",
                            "name": "John Doe",
                            "type": "INDIVIDUAL",
                            "setup_intent_id": "seti_ABC123xyz"
                        }
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(
            description="Profile does not have a setup_intent_id or invalid request",
            examples=[
                OpenApiExample(
                    "Missing Setup Intent",
                    value={"detail": "Profile does not have a setup_intent_id"},
                    response_only=True
                )
            ]
        ),
        404: OpenApiResponse(
            description="Profile not found",
            examples=[
                OpenApiExample(
                    "Profile Not Found",
                    value={"detail": "Profile not found"},
                    response_only=True
                )
            ]
        )
    },
    tags=["Profile Management"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stripe_intent_id_view(request):
    """Get Stripe Setup Intent ID - Authenticated Endpoint"""
    
    # Fetch the profile for the logged-in user
    try:
        profile = request.user.profile  # assuming OneToOne relation: user.profile
    except Profile.DoesNotExist:
        return Response(
            {'detail': 'Profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if not profile.setup_intent_id:
        return Response(
            {'detail': 'Profile does not have a setup_intent_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {
            'message': 'Profile retrieved successfully',
            'profile': {
                'id': str(profile.id),
                'name': profile.name,
                'type': profile.type,
                'setup_intent_id': profile.setup_intent_id,
            }
        },
        status=status.HTTP_200_OK
    )


@extend_schema(
    summary="Update Stripe Subscription ID",
    description="""
Update the Stripe subscription ID for a subscription.

**Authentication:** None required (public endpoint)

**Request Body:**
- `subscription_id` (uuid, required): The UUID of the subscription to update
- `stripe_subscription_id` (string, required): New Stripe subscription ID to set

**Response:**
- Updated subscription details
- List of updated fields
""",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'subscription_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Subscription UUID'
                },
                'stripe_subscription_id': {
                    'type': 'string',
                    'description': 'New Stripe subscription ID'
                }
            },
            'required': ['subscription_id', 'stripe_subscription_id']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Subscription updated successfully",
            examples=[
                OpenApiExample(
                    "Success Response",
                    value={
                        "message": "Subscription updated successfully",
                        "subscription": {
                            "id": "123e4567-e89b-12d3-a456-426614174002",
                            "profile_id": "123e4567-e89b-12d3-a456-426614174001",
                            "stripe_subscription_id": "sub_ABC123xyz",
                            "updated_at": "2026-02-05T10:30:00Z"
                        },
                        "updated_fields": ["stripe_subscription_id"]
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(description="Invalid request data"),
        404: OpenApiResponse(description="Subscription not found")
    },
    examples=[
        OpenApiExample(
            "Update Stripe Subscription ID",
            value={
                "subscription_id": "123e4567-e89b-12d3-a456-426614174002",
                "stripe_subscription_id": "sub_ABC123xyz"
            },
            request_only=True
        )
    ],
    tags=["Subscription Management"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def update_stripe_subscription_id_view(request):
    """Update only the stripe_subscription_id of a subscription"""
    
    subscription_id = request.data.get("subscription_id")
    stripe_subscription_id = request.data.get("stripe_subscription_id")
    
    if not subscription_id or not stripe_subscription_id:
        return Response(
            {"detail": "subscription_id and stripe_subscription_id are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Fetch subscription
    try:
        subscription = Subscription.objects.get(id=subscription_id)
    except Subscription.DoesNotExist:
        return Response({"detail": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Update stripe_subscription_id
    subscription.stripe_subscription_id = stripe_subscription_id.strip()
    subscription.save(update_fields=['stripe_subscription_id', 'updated_at'])
    
    return Response({
        "message": "Subscription updated successfully",
        "subscription": {
            "id": str(subscription.id),
            "profile_id": str(subscription.profile.id),
            "stripe_subscription_id": subscription.stripe_subscription_id,
            "updated_at": subscription.updated_at.isoformat()
        },
        "updated_fields": ["stripe_subscription_id"]
    }, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cancel_subscription_view(request, subscription_id):
    """
    Cancel a subscription.

    Used when:
    1. User manually cancels trial before it ends.
    2. System cancels existing trial before creating a new subscription.
    """

    profile = request.user.profile

    # Ensure subscription belongs to logged-in user's profile
    try:
        subscription = Subscription.objects.get(
            id=subscription_id,
            profile=profile
        )
    except Subscription.DoesNotExist:
        return Response(
            {"detail": "Subscription not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Prevent canceling already canceled subscriptions
    if subscription.status in [
        SubscriptionStatus.CANCELED,
        SubscriptionStatus.INCOMPLETE_EXPIRED,
    ]:
        return Response(
            {"detail": "Subscription is already canceled."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get canceled_at from payload or default to now
    canceled_at = request.data.get("canceled_at")
    if canceled_at:
        try:
            canceled_at = timezone.datetime.fromisoformat(
                canceled_at.replace("Z", "+00:00")
            )
        except ValueError:
            return Response(
                {"detail": "Invalid canceled_at format. Use ISO 8601 format."},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        canceled_at = timezone.now()

    # Update subscription
    subscription.status = SubscriptionStatus.CANCELED
    subscription.cancel_at = canceled_at
    subscription.cancel_at_period_end = False
    subscription.save(update_fields=["status", "cancel_at", "cancel_at_period_end", "updated_at"])

    return Response(
        {
            "detail": "Subscription canceled successfully.",
            "subscription": {
                "id": str(subscription.id),
                "status": subscription.status,
                "canceled_at": subscription.cancel_at.isoformat(),
            }
        },
        status=status.HTTP_200_OK
    )