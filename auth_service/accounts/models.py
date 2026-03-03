import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager,PermissionsMixin
from django.utils.timezone import now


class UserType(models.TextChoices):
    INDIVIDUAL = 'INDIVIDUAL', 'Individual'
    ORGANIZATION = 'ORGANIZATION', 'Organization'


class PlanName(models.TextChoices):
    FREE_ESIGN = 'FREE_ESIGN', 'Free eSign'
    ESIGN = 'ESIGN', 'eSign'
    EDMS_PLUS = 'EDMS_PLUS', 'EDMS+'


class SubscriptionStatus(models.TextChoices):
    INCOMPLETE = 'incomplete', 'Incomplete'
    INCOMPLETE_EXPIRED = 'incomplete_expired', 'Incomplete Expired'
    TRIALING = 'trialing', 'Trialing'
    ACTIVE = 'active', 'Active'
    PAST_DUE = 'past_due', 'Past Due'
    CANCELED = 'canceled', 'Canceled'
    UNPAID = 'unpaid', 'Unpaid'


class SubscriptionEventType(models.TextChoices):
    CREATED = 'created'
    TRIAL_STARTED = 'trial_started'
    TRIAL_ENDED = 'trial_ended'
    ACTIVATED = 'activated'
    UPGRADED = 'upgraded'
    DOWNGRADED = 'downgraded'
    PAYMENT_FAILED = 'payment_failed'
    CANCELED = 'canceled'
    REACTIVATED = 'reactivated'

class OrderStatus(models.TextChoices):
    PROCESSING = 'processing', 'Processing'
    CONFIRMED = 'confirmed', 'Confirmed'
    REJECTED = 'rejected', 'Rejected'
    CANCELED = 'canceled', 'Canceled'


class BillingInterval(models.TextChoices):
    MONTHLY = 'MONTHLY', 'Monthly'
    YEARLY = 'YEARLY', 'Yearly'
    NONE = 'NONE', 'None'


class UserManager(BaseUserManager):
    """Custom user manager for User model."""

    def create_user(self, email, password=None, **extra_fields):
            if not email:
                raise ValueError('Email is required')
            email = self.normalize_email(email)
            user = self.model(email=email, **extra_fields)
            if password:
                user.set_password(password)
            user.save(using=self._db)
            return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_active', True)

        if not extra_fields.get('profile'):
            raise ValueError('Superuser must have a profile')

        return self.create_user(email, password, **extra_fields)



class Profile(models.Model):
    """Organization or User Profile."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=UserType.choices)
    org_name = models.CharField(max_length=255, null=True, blank=True)
    setup_intent_id  = models.CharField(max_length=255, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'profiles'
        verbose_name_plural = 'profiles'


    def first_user(self):
        """
        Returns the first user associated with this profile, or None if no users exist.
        """
        return self.users.first()

    def __str__(self):
        return f"{self.name} ({self.type})"


# class Order(models.Model):
#     """Order model for tracking user orders."""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='orders')
#     order_id = models.CharField(max_length=255, unique=True)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     order_status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PROCESSING)

#     class Meta:
#         db_table = 'orders'
#         verbose_name_plural = 'orders'

#     def __str__(self):
#         return f"Order {self.order_id} - {self.status}"



class TrialHistory(models.Model):
    """Trial history for profiles."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='trial_histories')
    plan_name = models.CharField(max_length=20, choices=PlanName.choices)
    started_at = models.DateTimeField(default=now)
    ended_at = models.DateTimeField(null=True, blank=True)  # Actual end date (can be before trial_end if converted early)
    trial_end = models.DateTimeField()  # Scheduled end date (always 14 days from start)
    converted_to_subscription = models.BooleanField(default=False)
    conversion_date = models.DateTimeField(null=True, blank=True)  # Track when conversion happened
    early_conversion = models.BooleanField(default=False)  # True if converted before trial_end
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trial_histories'
        verbose_name_plural = 'trial_histories'

    def __str__(self):
        return f"Trial for {self.profile.name} - {self.plan_name} started at {self.started_at}"

class Subscription(models.Model):
    """Subscription model for profiles."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='subscription')
    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True)
    plan_name = models.CharField(max_length=20, choices=PlanName.choices)
    no_of_licenses = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices)
    billing_interval = models.CharField(max_length=20, choices=BillingInterval.choices)
    pending_billing_interval = models.CharField(max_length=20, null=True, blank=True)
    pending_number_of_licenses = models.IntegerField(default=1)
    start_date = models.DateTimeField(auto_now_add=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    cancel_at = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    last_3day_reminder_sent = models.DateTimeField(null=True, blank=True)
    last_1day_reminder_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   

    class Meta:
        db_table = 'subscriptions'
        verbose_name_plural = 'subscriptions'

    def __str__(self):
        return f"{self.plan_name} - {self.profile.name}"


class SubscriptionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='events'
    )
    event_type = models.CharField(max_length=30, choices=SubscriptionEventType.choices)
    
    # Snapshot of state at time of event
    plan_name = models.CharField(max_length=20, choices=PlanName.choices, null=True, blank=True)
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, null=True, blank=True)
    billing_interval = models.CharField(max_length=20, choices=BillingInterval.choices, null=True, blank=True)
    no_of_licenses = models.IntegerField(null=True, blank=True)
    
    # What changed (previous vs new)
    previous_plan_name = models.CharField(max_length=20, null=True, blank=True)
    previous_status = models.CharField(max_length=20, null=True, blank=True)
    previous_billing_interval = models.CharField(max_length=20, null=True, blank=True)
    previous_no_of_licenses = models.IntegerField(null=True, blank=True)

    # Extra context (source, stripe event id, etc)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subscription_events'
        ordering = ['-created_at']



class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model."""
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    email_verification_token = models.CharField(max_length=64, null=True, blank=True)
    email_verification_token_expires = models.DateTimeField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    has_license = models.BooleanField(default=False)
    license_assigned_at = models.DateTimeField(null=True, blank=True)
    password_reset_token = models.CharField(max_length=64, null=True, blank=True)
    password_reset_token_expires = models.DateTimeField(null=True, blank=True)
    username = models.CharField(max_length=255, unique=True,null=True, blank=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    is_domain_user = models.BooleanField(default=False)
    domain = models.CharField(max_length=255, null=True, blank=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='users')
    is_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email