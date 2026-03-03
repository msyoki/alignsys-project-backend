"""
User Management Views

This module contains API endpoints for:
- Retrieving organization users
- Retrieving all users (admin only)
- User profile management

All endpoints require authentication via JWT Bearer token.
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from uuid import UUID
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from .authentication import JWTAuthentication
from .serializers import UserSerializer
from .models import Profile

User = get_user_model()


# ============================================================================
# USER RETRIEVAL ENDPOINTS
# ============================================================================

@extend_schema(
    summary="Get Organization Users",
    description="""
Retrieve all users belonging to a specific organization profile.

**Authentication:** Bearer token required

**Authorization:**
- Admin users can access any organization's users.
- Regular users can only access their own organization's users.

**Path Parameters:**
- `profile_id` (UUID, required): UUID of the organization profile.

**Headers:**
- `Authorization`: Bearer <access_token>

**Response:**
- Array of user objects with full profile information.

**Use Cases:**
- Organization admins viewing their team members.
- HR systems listing employees.
- User permission management interfaces.
""",
    parameters=[
        OpenApiParameter(
            name='profile_id',
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description='UUID of the organization profile',
            required=True,
            examples=[
                OpenApiExample(
                    'Valid Profile ID',
                    value='123e4567-e89b-12d3-a456-426614174001'
                )
            ],
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=UserSerializer(many=True),
            description="Successfully retrieved organization users",
            examples=[
                OpenApiExample(
                    'Organization Users List',
                    value={
                        "profile": {
                            "id": "123e4567-e89b-12d3-a4354-426614174001",
                            "name": "ACME Administrators",
                            "type": "ACME",
                            "org_name": "Corp",
                            "stripe_customer_id": "cus_1234567890",
                            "created_at": "2026-02-04T09:13:47.212599+00:00"
                        },
                        "users": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "email": "admin@acme.com",
                                "username": "admin",
                                "first_name": "Admin",
                                "last_name": "User",
                                "is_domain_user": False,
                                "domain": None,
                                "profile": "123e4567-e89b-12d3-a456-426614174001",
                                "is_admin": True,
                                "is_active": True,
                                "created_at": "2025-01-01T10:00:00Z"
                            },
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174002",
                                "email": "user1@acme.com",
                                "username": "user1",
                                "first_name": "John",
                                "last_name": "Doe",
                                "is_domain_user": False,
                                "domain": None,
                                "profile": "123e4567-e89b-12d3-a456-426614174001",
                                "is_admin": False,
                                "is_active": True,
                                "created_at": "2025-01-15T14:30:00Z"
                            },
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174003",
                                "email": "user2@acme.com",
                                "username": "user2",
                                "first_name": "Jane",
                                "last_name": "Smith",
                                "is_domain_user": True,
                                "domain": "acme.com",
                                "profile": "123e4567-e89b-12d3-a456-426614174001",
                                "is_admin": False,
                                "is_active": True,
                                "created_at": "2025-01-20T09:15:00Z"
                            }
                        ]
                    }
                    ,
                    response_only=True,
                )
            ],
        ),
        400: OpenApiResponse(
            description="Invalid profile_id format",
            examples=[
                OpenApiExample(
                    'Invalid UUID',
                    value={'detail': 'Invalid profile_id'},
                    response_only=True,
                )
            ],
        ),
        401: OpenApiResponse(
            description="Invalid or missing authentication token",
            examples=[
                OpenApiExample(
                    'Unauthorized',
                    value={'detail': 'Unauthorized'},
                    response_only=True,
                )
            ],
        ),
        403: OpenApiResponse(
            description="User not authorized to access this organization",
            examples=[
                OpenApiExample(
                    'Not Authorized',
                    value={'detail': 'Not authorized'},
                    response_only=True,
                )
            ],
        ),
        404: OpenApiResponse(
            description="Profile not found",
            examples=[
                OpenApiExample(
                    'Profile Not Found',
                    value={'detail': 'Profile not found'},
                    response_only=True,
                )
            ],
        ),
    },
    tags=['User Management'],
)
@api_view(['GET'])
def get_profile(request, profile_id):
    """
    Get all users in an organization.
    
    Retrieves a list of all users associated with a specific organization profile.
    Regular users can only access their own organization, while admins can access any.
    
    Args:
        request: HTTP request object with authentication
        profile_id: UUID string of the organization profile
        
    Returns:
        Response: JSON array of user objects or error message
        
    Status Codes:
        200: Success - returns list of users
        400: Invalid profile_id format
        401: Authentication failed
        403: Not authorized to access this organization
        404: Profile not found
    """
    auth = JWTAuthentication()
    auth_result = auth.authenticate(request)
    if not auth_result:
        return Response(
            {'detail': 'Unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    current_user = auth_result[0]
    
    try:
        profile_uuid = UUID(profile_id)
    except ValueError:
        return Response(
            {'detail': 'Invalid profile_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check authorization
    if not current_user.is_admin and current_user.profile_id != profile_uuid:
        return Response(
            {'detail': 'Not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        profile = Profile.objects.get(id=profile_uuid)
    except Profile.DoesNotExist:
        return Response(
            {'detail': 'Profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    users = User.objects.filter(profile=profile)
    serializer = UserSerializer(users, many=True)


    response = {
        'profile': {
            'id': str(profile.id),
            'name': profile.name,
            'type': profile.type,
            "stripe_customer_id": profile.stripe_customer_id,
            'created_at': profile.created_at.isoformat(),
        },
        'users': serializer.data
    }
    return Response(response, status=status.HTTP_200_OK)

@extend_schema(
    summary="Get All Users (Admin Only)",
    description="""
Retrieve a complete list of all users in the system.

**Authentication:** Bearer token required (Admin only)

**Authorization:**
- Only users with `is_admin=True` can access this endpoint.
- Returns users from all organizations and profiles.

**Headers:**
- `Authorization`: Bearer <access_token>

**Response:**
- Array of all user objects in the system.

**Use Cases:**
- System administration and user management.
- Audit and compliance reporting.
- User analytics and statistics.
- Global search across all users.

**Performance Notes:**
- This endpoint may return a large dataset.
- Consider implementing pagination for production use.
- Results include users from all organizations.
""",
    request=None,
    responses={
        200: OpenApiResponse(
            response=UserSerializer(many=True),
            description="Successfully retrieved all users",
            examples=[
                OpenApiExample(
                    'All Users List',
                    value=[
                        {
                            'id': '123e4567-e89b-12d3-a456-426614174000',
                            'email': 'admin@acme.com',
                            'username': 'admin',
                            'first_name': 'Admin',
                            'last_name': 'User',
                            'is_domain_user': False,
                            'domain': None,
                            'profile': '123e4567-e89b-12d3-a456-426614174001',
                            'is_admin': True,
                            'is_active': True,
                            'created_at': '2025-01-01T10:00:00Z'
                        },
                        {
                            'id': '223e4567-e89b-12d3-a456-426614174000',
                            'email': 'john.doe@example.com',
                            'username': 'johndoe',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'is_domain_user': False,
                            'domain': None,
                            'profile': '223e4567-e89b-12d3-a456-426614174001',
                            'is_admin': False,
                            'is_active': True,
                            'created_at': '2025-01-10T08:30:00Z'
                        },
                        {
                            'id': '323e4567-e89b-12d3-a456-426614174000',
                            'email': 'jane.smith@company.com',
                            'username': 'janesmith',
                            'first_name': 'Jane',
                            'last_name': 'Smith',
                            'is_domain_user': True,
                            'domain': 'company.com',
                            'profile': '323e4567-e89b-12d3-a456-426614174001',
                            'is_admin': False,
                            'is_active': True,
                            'created_at': '2025-01-15T12:00:00Z'
                        }
                    ],
                    response_only=True,
                )
            ],
        ),
        401: OpenApiResponse(
            description="Invalid or missing authentication token",
            examples=[
                OpenApiExample(
                    'Unauthorized',
                    value={'detail': 'Unauthorized'},
                    response_only=True,
                )
            ],
        ),
        403: OpenApiResponse(
            description="User is not an admin",
            examples=[
                OpenApiExample(
                    'Not Authorized - Not Admin',
                    value={'detail': 'Not authorized'},
                    response_only=True,
                )
            ],
        ),
    },
    tags=['User Management'],
)
@api_view(['GET'])
def get_all_users(request):
    """
    Get all users (admin only).
    
    Retrieves a complete list of all users in the system across all organizations.
    Access is restricted to administrators only.
    
    Args:
        request: HTTP request object with authentication
        
    Returns:
        Response: JSON array of all user objects or error message
        
    Status Codes:
        200: Success - returns complete list of users
        401: Authentication failed
        403: User is not an admin
        
    Security:
        - Requires valid JWT token
        - Requires is_admin=True
        - Returns sensitive user data - use appropriate access controls
    """
    auth = JWTAuthentication()
    auth_result = auth.authenticate(request)
    if not auth_result:
        return Response(
            {'detail': 'Unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    current_user = auth_result[0]
    
    if not current_user.is_admin:
        return Response(
            {'detail': 'Not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)