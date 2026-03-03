"""External service JWT authentication utilities.

This module provides JWT validation for external services (EDMS, DSS)
that authenticate against the centralized auth_service_django.
"""
import os
import requests
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ExternalServiceJWTAuth(BaseAuthentication):
    """
    Authenticate JWT tokens issued by auth_service_django.
    
    External services (EDMS, DSS) can use this class to validate
    tokens by calling the /auth/validate endpoint.
    
    Usage in Django settings:
        REST_FRAMEWORK = {
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'path.to.ExternalServiceJWTAuth',
            ]
        }
    """
    
    AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8000')
    VALIDATE_ENDPOINT = '/auth/validate'
    
    def authenticate(self, request):
        """Authenticate request using JWT token from Authorization header."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ', 1)[1]
        
        try:
            # Validate token with auth service
            user_data = self._validate_token(token)
            
            # Create a pseudo-user object from the response
            request.user_data = user_data
            return (user_data, None)
            
        except Exception as e:
            raise AuthenticationFailed(f'Invalid token: {str(e)}')
    
    def _validate_token(self, token: str) -> dict:
        """
        Validate JWT token by calling auth_service_django's validate endpoint.
        
        Returns:
            dict: User data from the validation response
            
        Raises:
            requests.RequestException: If validation request fails
            ValueError: If token is invalid
        """
        validate_url = f"{self.AUTH_SERVICE_URL}{self.VALIDATE_ENDPOINT}"
        
        try:
            response = requests.post(
                validate_url,
                json={'token': token},
                timeout=5
            )
            
            if response.status_code != 200:
                raise ValueError(f'Token validation failed: {response.text}')
            
            data = response.json()
            if not data.get('valid'):
                raise ValueError('Token is invalid or expired')
            
            return data.get('user', {})
            
        except requests.RequestException as e:
            raise ValueError(f'Could not reach auth service: {str(e)}')
    
    @staticmethod
    def get_tokens_for_user(auth_service_url: str, email: str, password: str) -> dict:
        """
        Obtain JWT tokens from auth_service_django for a user.
        
        Args:
            auth_service_url: Base URL of auth_service_django
            email: User email or username
            password: User password
            
        Returns:
            dict: Contains 'access' and 'refresh' tokens
            
        Raises:
            requests.RequestException: If login request fails
        """
        login_url = f"{auth_service_url}/auth/login"
        
        try:
            response = requests.post(
                login_url,
                json={'username': email, 'password': password},
                timeout=5
            )
            
            if response.status_code != 200:
                raise ValueError(f'Login failed: {response.text}')
            
            data = response.json()
            return {
                'access': data.get('access'),
                'refresh': data.get('refresh'),
                'user': data.get('user')
            }
            
        except requests.RequestException as e:
            raise ValueError(f'Could not reach auth service: {str(e)}')
