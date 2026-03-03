from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from rest_framework.exceptions import AuthenticationFailed
from authapp.utils import create_login_log, get_vault_count

User = get_user_model()

class InternalOrDomainAuthTokenSerializer(TokenObtainPairSerializer):
    def get_request(self):
        return self.context.get("request")

    def validate(self, attrs):
        print("internal authentication was called !!!")
        identifier = attrs.get("username")
        password = attrs.get("password")

        if not identifier or not password:
            raise AuthenticationFailed("Must include 'username' or 'email' and 'password'.")

        identifier = identifier.strip().lower()

        try:
            user = User.objects.get(Q(username__iexact=identifier) | Q(email__iexact=identifier))

        except User.DoesNotExist:
            raise AuthenticationFailed("No user found with this username or email.")

        # Use Django's authenticate to preserve consistency with TokenObtainPairSerializer
        auth_user = authenticate(
            request=self.context.get("request"),
            username=user.username,  # always authenticate by username
            password=password
        )

        if not auth_user:
            raise AuthenticationFailed("Incorrect password.")

        if not auth_user.is_active:
            raise AuthenticationFailed("User account is disabled.")
        
        attrs['username'] = user.username

        self.user = auth_user
        data = super().validate(attrs)

        # Optional: create login log
        request = self.get_request()
        create_login_log(auth_user, request)

        return data

    def get_token(self, user):
        token = super().get_token(user)
        vaultcount = get_vault_count(user)

        token_claims = {
            "id": str(user.pk),
            "username": str(user.username),
            "email": str(user.email),
            "vaultcount": str(vaultcount),
            "organization": str(user.organization.name if user.organization else ""),
            "organizationid": str(user.organization.id if user.organization else ""),
            "first_name": str(user.first_name),
            "last_name": str(user.last_name),
            "is_admin": str(user.is_admin),
            "is_superuser": str(user.is_superuser),
        }

        for key, value in token_claims.items():
            token[key] = value

        return token
