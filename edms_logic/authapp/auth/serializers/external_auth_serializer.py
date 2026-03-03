import requests
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import authenticate, get_user_model
from authapp.utils import get_client_ip
from django.conf import settings
from authapp.models import Vault,LoginLog
from user_agents import parse as parse_ua  # Add this import

User = get_user_model()
base_url=settings.BACKEND_API

class ExternalAuthTokenSerializer(TokenObtainPairSerializer):
    def get_request(self):
        return self.context.get("request")

    def authenticate_via_external_api(self, username, password, domain):
        """ Authenticate the domain user via an external API """
        api_url = f'{base_url}/api/UserAccounts/DomainAuth'
        payload = {
            "domain": domain,
            "username": username,
            "password": password
        }
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json"
        }

        print(f"Sending authentication request to {api_url} with payload: {payload}")
        response = requests.post(api_url, json=payload, headers=headers)

        if response.status_code == 200:
            print("✅ Authentication successful")
            return True

        print(f"❌ Authentication failed. Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        return False
    
    def get_token(self, user):
        """ Generate a JWT token with additional user details """
        token = super().get_token(user)

        vault_count = Vault.objects.filter(organization=user.organization).count() if user.organization else 0

        token['id'] = str(user.pk)
        token['username'] = str(user.username)
        token['email'] = str(user.email)
        token['vaultcount'] = str(vault_count)
        token['organization'] = str(user.organization.name) if user.organization else ""
        token['organizationid'] = str(user.organization.id) if user.organization else ""
        token['first_name'] = str(user.first_name)
        token['last_name'] = str(user.last_name)
        token['is_admin'] = str(user.is_admin)
        token['is_superuser'] = str(user.is_superuser)

        return token


    def validate(self, attrs):
        print("external authentication was called !!!")
        identifier = attrs.get("username")  # could be username or email
        password = attrs.get("password")

        request = self.get_request()

        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid username or password.")

        print(identifier)
        print(password)

        if not identifier or not password:
            raise AuthenticationFailed("Must include 'username' or 'email' and 'password'.")

        if user.is_domain_user:
            domain = user.domain
            if not self.authenticate_via_external_api(identifier, password, domain):
                raise AuthenticationFailed("External authentication failed.")
        else:
            user = authenticate(username=identifier, password=password)
            if user is None:
                raise AuthenticationFailed("Invalid username or password.")
            
      
        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        self.user = user  # Required for TokenObtainPairSerializer
   
        # ✅ Logging IP, user agent, device info
        ip = get_client_ip(request) if request else None
        user_agent_str = request.META.get('HTTP_USER_AGENT', '') if request else ''
        auth_source = 'external' if user.is_domain_user else 'internal'

        browser = os = device_type = platform = None
        if user_agent_str:
            ua = parse_ua(user_agent_str)
            browser = f"{ua.browser.family} {ua.browser.version_string}"
            os = f"{ua.os.family} {ua.os.version_string}"
            device_type = (
                "Mobile" if ua.is_mobile else
                "Tablet" if ua.is_tablet else
                "PC" if ua.is_pc else
                "Bot" if ua.is_bot else
                "Other"
            )
            platform = ua.device.family

        try:
            LoginLog.objects.create(
                user=user,
                ip_address=ip,
                user_agent=user_agent_str,
                browser=browser,
                os=os,
                device_type=device_type,
                platform=platform,
                auth_source=auth_source
            )
        except Exception as e:
            print(f"⚠️ Failed to log login event: {e}")

        # Generate token
        token = self.get_token(user)
        return {
            'refresh': str(token),
            'access': str(token.access_token),
            'user': {
                'id': user.pk,
                'username': user.username,
                'email': user.email,
                'vaultcount': Vault.objects.filter(organization=user.organization).count() if user.organization else 0,
                'organization': user.organization.name if user.organization else "",
                'organizationid': user.organization.id if user.organization else "",
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_admin': user.is_admin,
                'is_superuser': user.is_superuser,
            }
        }
