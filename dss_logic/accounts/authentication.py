# accounts/authentication.py
from rest_framework import authentication, exceptions
import requests
from django.conf import settings
from .models import User  # Your custom user model

class CentralizedJWTAuthentication(authentication.BaseAuthentication):
    """
    Authenticate requests using a centralized JWT auth API.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                return None
        except ValueError:
            return None

        # Verify token via central auth API
        verify_url = f"{settings.CENTRAL_AUTH_API['BASE_URL']}{settings.CENTRAL_AUTH_API['TOKEN_VERIFY_ENDPOINT']}"
        try:
            response = requests.post(verify_url, json={"token": token})
            response.raise_for_status()
        except requests.RequestException:
            raise exceptions.AuthenticationFailed("Could not verify token with central auth API")

        user_data = response.json()
        try:
            user = User.objects.get(id=user_data['user_id'])
        except User.DoesNotExist:
            # Optionally: auto-create the user
            user = User.objects.create(
                id=user_data['user_id'],
                username=user_data.get('username', f"user{user_data['user_id']}"),
                email=user_data.get('email', '')
            )

        return (user, token)