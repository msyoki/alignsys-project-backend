"""Authentication utilities using Simple JWT."""
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication as SimpleJWTAuthentication

User = get_user_model()


def get_tokens_for_user(user):
    """Generate refresh and access tokens for a user."""
    refresh = RefreshToken.for_user(user)
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def build_user_claims(user) -> dict:
    """Build JWT claims from user."""
    return {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "profile_id": str(user.profile_id),
        "is_admin": user.is_admin,
        "is_domain_user": user.is_domain_user,
    }


def build_user_payload(user) -> dict:
    """Build user payload for responses."""
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile_id": str(user.profile_id),
        "is_admin": user.is_admin,
        "is_domain_user": user.is_domain_user,
        "domain": user.domain,
    }


# Use Simple JWT's authentication class directly
JWTAuthentication = SimpleJWTAuthentication
