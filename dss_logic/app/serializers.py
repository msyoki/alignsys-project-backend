# accounts/serializers.py

from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from django.conf import settings
from django.contrib.auth import get_user_model
import requests

from .models import User, Company
from .models import SMTPConfigs
from app.models import Document  # adjust if needed

User = get_user_model()

# ----------------- Registration Serializers -----------------

class RegisterSerializer(ModelSerializer):
    password1 = serializers.CharField(max_length=128, min_length=8, write_only=True)
    password2 = serializers.CharField(max_length=128, min_length=8, write_only=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name','password1','password2','phone','company')

    def save(self):
        email = self.validated_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Duplicate email")
        
        password1 = self.validated_data['password1']
        password2 = self.validated_data['password2']
        if password1 != password2:
            raise serializers.ValidationError("Passwords don't match")

        user = User(
            email=email,
            first_name=self.validated_data['first_name'],
            last_name=self.validated_data['last_name'],
            phone=self.validated_data['phone'],
            company=self.validated_data['company']
        )
        user.set_password(password1)
        user.save()
        return user


class RegisterAdminSerializer(ModelSerializer):
    password1 = serializers.CharField(max_length=128, min_length=8, write_only=True)
    password2 = serializers.CharField(max_length=128, min_length=8, write_only=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name','password1','password2','company','is_admin')

    def save(self):
        email = self.validated_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Duplicate email")
        
        password1 = self.validated_data['password1']
        password2 = self.validated_data['password2']
        if password1 != password2:
            raise serializers.ValidationError("Passwords don't match")

        user = User(
            email=email,
            first_name=self.validated_data['first_name'],
            last_name=self.validated_data['last_name'],
            is_admin=self.validated_data['is_admin'],
            company=self.validated_data['company']
        )
        user.set_password(password1)
        user.save()
        return user


# ----------------- Centralized Login Serializer -----------------

class CentralizedLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data['email']
        password = data['password']

        # Call centralized auth API to obtain tokens
        url = f"{settings.CENTRAL_AUTH_API['BASE_URL']}/auth/login"
        print("Centralized Auth API URL:", url)  # Debugging line
        print("Centralized Auth API Payload:", {"username": email, "password": password})  # Debugging line
        response = requests.post(url, json={"username": email, "password": password})
        #print("Centralized Auth API Response:", response.status_code, response.text)  # Debugging line
        print("Centralized Auth API Response:", response.status_code)  # Debugging line
        if response.status_code != 200:
            raise serializers.ValidationError("Invalid credentials")

        tokens = response.json()
        access_token = tokens.get("access")
        refresh_token = tokens.get("refresh")

        # Fetch user info from centralized API (assumes /me/ endpoint)
        user_info_url = f"{settings.CENTRAL_AUTH_API['BASE_URL']}/auth/me/"
        headers = {"Authorization": f"Bearer {access_token}"}
        user_info_resp = requests.get(user_info_url, headers=headers)

        if user_info_resp.status_code != 200:
            raise serializers.ValidationError("Failed to fetch user info from central auth API")

        user_data = user_info_resp.json()

        # Auto-create or update local user
        user, created = User.objects.update_or_create(
            email=user_data['email'],  # local unique key
            defaults={
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "is_active": True,
                # store central UUID if you want:
                "central_id": user_data["id"],
            }
        )

        data['user'] = user
        data['access'] = access_token
        data['refresh'] = refresh_token
        return data


# ----------------- Other Serializers -----------------

class UserAvatar(ModelSerializer):
    avatar_url = serializers.SerializerMethodField('get_image_url')

    class Meta:
        model = User
        fields = ('pk','avatar_url')

    def get_image_url(self,obj):
        return obj.avatar.url if obj.avatar else None


class CompanyLogo(ModelSerializer):
    logo_url = serializers.SerializerMethodField('get_image_url')

    class Meta:
        model = Company
        fields = ('pk','logo_url')

    def get_image_url(self,obj):
        return obj.logo.url if obj.logo else None


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('email','first_name','last_name','avatar','is_active','is_licensed','is_admin','phone','mailtoall')


class CompanySerializer(ModelSerializer):
    class Meta:
        model = Company
        fields = ('name','email','approved','active','logo')


class RegisterCompanySerializer(ModelSerializer):
    class Meta:
        model = Company
        fields = ('name','email')


class SMTPConfigsSerializer(ModelSerializer):
    class Meta:
        model = SMTPConfigs
        fields = ['port', 'url', 'username', 'password', 'user','company','display_name']

    def validate_user(self, value):
        if not value:
            raise serializers.ValidationError("User cannot be empty.")
        return value


class CompleteSerializer(ModelSerializer):
    signedcomplete = serializers.SerializerMethodField()
    declined = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['guid', 'title', 'owner', 'docdate', 'signedcomplete', 'signeddate', 'declined']

    def get_signedcomplete(self, obj):
        return str(obj.signedcomplete)

    def get_declined(self, obj):
        return str(obj.declined)

    def get_owner(self, obj):
        return obj.userid.email if obj.userid else None