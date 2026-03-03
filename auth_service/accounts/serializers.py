from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PlanName, Profile, Subscription, UserType, BillingInterval,SubscriptionStatus
from email_validator import validate_email, EmailNotValidError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'name', 'type', 'org_name', 'created_at', 'updated_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan_name', 'status', 'no_of_licenses',
            'billing_interval', 'start_date', 'trial_end',
            'current_period_end', 'created_at', 'updated_at'
        ]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_domain_user', 'domain', 'profile', 'is_admin',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=255, write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    token_type = serializers.CharField(default='bearer', read_only=True)
    user = UserSerializer(read_only=True)


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RegisterRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    profile_type = serializers.ChoiceField(choices=UserType.choices, default=UserType.INDIVIDUAL)
    org_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    # trial_end removed - now calculated automatically as 14 days

class RegisterResponseSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    profile_id = serializers.CharField(read_only=True)
    is_admin = serializers.BooleanField(read_only=True)



# class SubscriptionRequestSerializer(serializers.Serializer):
#     profile_id = serializers.CharField(max_length=36)
#     setup_intent_id = serializers.CharField(required=False, allow_null=True, default=None)
#     stripe_subscription_id = serializers.CharField(required=False, allow_null=True, default=None)
#     plan_name = serializers.ChoiceField(choices=PlanName.choices, default=PlanName.ESIGN)
#     status = serializers.ChoiceField(choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING)
#     billing_interval = serializers.ChoiceField(choices=BillingInterval.choices, default=BillingInterval.MONTHLY)
#     no_of_licenses = serializers.IntegerField(min_value=1, default=1)
#     start_date = serializers.DateField(allow_null=True, default=None)
#     trial_end = serializers.DateField(allow_null=True, default=None)
#     current_period_end = serializers.DateField(allow_null=True, default=None)
#     cancel_at =serializers.DateField(allow_null=True, default=None)
#     cancel_at_period_end =serializers.DateField(allow_null=True, default=None)
#     pending_billing_interval = serializers.CharField(required=False, allow_null=True, default=None)
#     pending_number_of_licenses = serializers.IntegerField(min_value=1,allow_null=True, default=None)   


class SubscriptionRequestSerializer(serializers.Serializer):
    profile_id = serializers.CharField(max_length=36, required=False, allow_null=True)

    subscription_id = serializers.CharField(
        required=False, 
        allow_null=True, 
        allow_blank=True
    )
  
    stripe_subscription_id = serializers.CharField(
        required=False, 
        allow_null=True, 
        allow_blank=True
    )
    plan_name = serializers.ChoiceField(
        choices=PlanName.choices, 
    )
    status = serializers.ChoiceField(
        choices=SubscriptionStatus.choices, 
        required=False
    )
    billing_interval = serializers.ChoiceField(
        choices=BillingInterval.choices, 
        required=False, 
        allow_null=True
    )
    no_of_licenses = serializers.IntegerField(
        min_value=1, 
        default=1
    )
    start_date = serializers.DateTimeField(
        required=False, 
        allow_null=True
    )
    trial_end = serializers.DateTimeField(
        required=False, 
        allow_null=True
    )
    current_period_end = serializers.DateTimeField(
        required=False, 
        allow_null=True
    )
    cancel_at = serializers.DateTimeField(
        required=False, 
        allow_null=True
    )
    cancel_at_period_end = serializers.BooleanField(
        default=False
    )
    pending_billing_interval = serializers.CharField(
        required=False, 
        allow_null=True, 
        allow_blank=True
    )
    pending_number_of_licenses = serializers.IntegerField(
        min_value=1, 
        required=False, 
        allow_null=True
    )


    def to_internal_value(self, data):
        data = data.copy()

        if "status" in data and isinstance(data["status"], str):
            data["status"] = data["status"].lower()

        return super().to_internal_value(data)
    
class AddOrgUserRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=255, write_only=True)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    profile_id = serializers.CharField(max_length=36)


class VerifyEmailRequestSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, help_text="Email verification token from the email link")


class VerifyEmailResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    email = serializers.EmailField()


class ResendVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="User email address")


class ResendVerificationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


# Add these to your serializers file

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="Email address of the account")


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, help_text="Password reset token from email")
    new_password = serializers.CharField(
        required=True, 
        min_length=8,
        help_text="New password (minimum 8 characters)"
    )
    confirm_password = serializers.CharField(
        required=True,
        help_text="Confirm new password"
    )

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data


class PasswordResetRequestResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class PasswordResetConfirmResponseSerializer(serializers.Serializer):
    message = serializers.CharField()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        profile = getattr(user, "profile", None)
        subscription = getattr(profile, "subscription", None) if profile else None

        # Custom claims
        token['user_id'] = str(user.id)
        token['username'] = user.username
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['profile_id'] = str(profile.id) if profile else None
        token['stripe_subscription_id'] = (
            str(subscription.stripe_subscription_id) if subscription else None
        )
        return token
    

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
        help_text="Current password of the user"
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
        help_text="New password (minimum 8 characters)"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
        help_text="Confirm new password"
    )

    def validate(self, attrs):
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': "Passwords do not match"
            })

        return attrs