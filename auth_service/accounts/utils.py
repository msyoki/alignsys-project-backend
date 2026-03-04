from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework_simplejwt.tokens import AccessToken
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from .models import Profile, UserType, PlanName, TrialHistory, Subscription, SubscriptionStatus,User,BillingInterval,SubscriptionEventType

from django.utils.timezone import now
from datetime import timedelta
import re
import random
import string

User = get_user_model()


# ----------------------------
# USER LOOKUP
# ----------------------------
def get_user_by_identifier(identifier: str):
    """
    Fetch user by email or username.
    """
    identifier = identifier.strip().lower()

    try:
        return User.objects.get(email=identifier)
    except User.DoesNotExist:
        try:
            return User.objects.get(username=identifier)
        except User.DoesNotExist:
            return None


# ----------------------------
# TOKEN VALIDATION
# ----------------------------
def validate_jwt_token(token: str):
    """
    Validate JWT access token and return associated user.
    """
    try:
        access_token = AccessToken(token)
        user_id = access_token.get("user_id")  # key is usually 'user_id'
        return User.objects.get(id=user_id)
    except (ObjectDoesNotExist, Exception):
        return None


# ----------------------------
# RESPONSE BUILDER
# ----------------------------
def build_register_response(user):
    """
    Standard registration response payload.
    """
    profile = user.profile

    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile": {
            "id": str(profile.id),
            "name": profile.name,
            "type": profile.type,
            "org_name": profile.org_name,
        },
        "is_admin": user.is_admin,
        "is_active": user.is_active,
    }


# ----------------------------
# ORG USER CREATION
# ----------------------------
@transaction.atomic
def create_org_user(data):
    """
    Create a user under an existing organization profile.
    Admin-only action.
    """
    profile_id = data.get("profile_id")

    profile = Profile.objects.filter(
        id=profile_id,
        type=UserType.ORGANIZATION
    ).first()

    if not profile:
        raise ValueError("Organization profile not found")

    user = User.objects.create_user(
        email=data["email"].strip().lower(),
        username=data["username"],
        password=data["password"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        profile=profile,
        is_admin=False,
        is_active=True,
    )

    return user


# ----------------------------
# NORMALIZE PLAN NAME
# ----------------------------

def normalize_plan_name(value):
    """
    Normalize a plan name to a PlanName enum member.
    Accepts numeric strings, uppercase, lowercase, or common variants.
    """
    if not value:
        raise ValueError("Plan name cannot be empty or None")

    raw = str(value).strip().upper()
    
    # Remove non-alphanumeric characters for forgiving match
    cleaned = re.sub(r'[^A-Z0-9]', '', raw)

    if cleaned in ("FREEESIGN", "0"):
        return PlanName.FREE_ESIGN
    elif cleaned in ("ESIGN", "1"):
        return PlanName.ESIGN
    elif cleaned in ("EDMS", "EDMSPLUS", "2"):
        return PlanName.EDMS_PLUS

    raise ValueError(f"Invalid plan name: {value}")


# ----------------------------
# NORMALIZE SUBSCRIPTION STATUS
# ----------------------------

def normalize_subscription_status(value):
    normalized = value.lower()
    valid_values = [choice[0] for choice in SubscriptionStatus.choices]

    if normalized not in valid_values:
        raise serializers.ValidationError("Invalid subscription status")

    return normalized


# ----------------------------
# NORMALIZE BILLING INTERVAL
# ----------------------------
def normalize_billing_interval(value):
    """
    Normalize a billing interval to a BillingInterval enum member.
    Accepts numeric strings, uppercase, lowercase, or common variants.
    
    Rules:
    - 'MONTHLY', 'M', '0' → BillingInterval.MONTHLY
    - 'YEARLY', 'Y', '1' → BillingInterval.YEARLY
    - 'NONE', 'N', '', '2', None → BillingInterval.NONE
    """
    if value is None:
        return BillingInterval.NONE

    raw = str(value).strip().upper()

    # Remove non-alphanumeric characters for forgiving match
    cleaned = re.sub(r'[^A-Z0-9]', '', raw)

    if cleaned in ("MONTHLY", "M", "0"):
        return BillingInterval.MONTHLY
    elif cleaned in ("YEARLY", "Y", "1"):
        return BillingInterval.YEARLY
    elif cleaned in ("NONE", "N", "", "2"):
        return BillingInterval.NONE

    raise ValueError(f"Invalid billing interval: {value}")



# ----------------------------
# TRIAL MANAGEMENT
# ----------------------------
TRIAL_PERIOD_DAYS = 14



def can_start_trial(profile, plan_name):
    """
    Check if a profile can start a trial for the given plan.

    PLAN RULES:
    1. FREE_ESIGN: Free for life, no trial needed (always allowed)
    2. ESIGN: Can trial if never trialed ESIGN or EDMS_PLUS before
    3. EDMS_PLUS: Can trial if never trialed EDMS_PLUS before (can trial even after ESIGN trial)

    TRIAL RULES:
    - Cannot start a trial if currently in an active trial
    - Must respect cooldown (TRIAL_PERIOD_DAYS) for past trials
    - EDMS_PLUS includes ESIGN features (ESIGN cannot be trialed after EDMS_PLUS)

    Args:
        profile: User profile
        plan_name: Plan to check (PlanName enum)

    Returns:
        tuple: (can_start: bool, error_message: str or None)
    """
    # Fetch all trial histories for the profile
    trial_histories = TrialHistory.objects.filter(profile=profile)

    # Check for active trials
    active_trial = trial_histories.filter(ended_at__isnull=True).first()
    if active_trial:
        return False, f"Cannot start a new trial while {active_trial.plan_name} trial is active"

    # Check past trials within cooldown period
    last_trial = trial_histories.order_by('-started_at').first()
    if last_trial and last_trial.started_at + timedelta(days=TRIAL_PERIOD_DAYS) > now():
        return False, f"You must wait {TRIAL_PERIOD_DAYS} days between trials"

    # Flags for past trialed plans
    has_trialed_esign = trial_histories.filter(plan_name=PlanName.ESIGN).exists()
    has_trialed_edms_plus = trial_histories.filter(plan_name=PlanName.EDMS_PLUS).exists()

    # FREE_ESIGN - No trial needed, it's free for life
    if plan_name == PlanName.FREE_ESIGN:
        return True, None

    # ESIGN trial eligibility
    elif plan_name == PlanName.ESIGN:
        if has_trialed_edms_plus:
            return False, "Cannot trial eSign after trialing EDMS+ (EDMS+ includes all eSign features)"
        if has_trialed_esign:
            return False, "You have already used your eSign trial"
        return True, None

    # EDMS_PLUS trial eligibility
    elif plan_name == PlanName.EDMS_PLUS:
        if has_trialed_edms_plus:
            return False, "You have already used your EDMS+ trial"
        # Can trial EDMS_PLUS even if already trialed ESIGN
        return True, None

    # Catch-all for invalid plans
    return False, "Invalid plan for trial"


def create_trial_history(profile, plan_name, subscription):
    """
    Create a trial history record when a user starts a trial.
    Only creates if subscription status is TRIALING.
    Automatically sets trial end date to 14 days from now.
    
    Note: FREE_ESIGN should never have trial status as it's free for life.
    
    Args:
        profile: User profile
        plan_name: Plan name (PlanName enum)
        subscription: Subscription object
    
    Returns:
        TrialHistory object or None
    """
    # FREE_ESIGN should never be in trial status
    if plan_name == PlanName.FREE_ESIGN:
        return None
    
    if subscription.status == SubscriptionStatus.TRIALING:
        trial_end_date = now() + timedelta(days=TRIAL_PERIOD_DAYS)
        
        trial_history = TrialHistory.objects.create(
            profile=profile,
            plan_name=plan_name,
            started_at=now(),
            trial_end=trial_end_date,  # Scheduled end
            ended_at=None  # Actual end (set when trial ends or converts)
        )
        
        # Update the subscription trial_end
        subscription.trial_end = trial_end_date
        subscription.current_period_end = trial_end_date
        subscription.save()
        
        return trial_history
    return None


def cancel_trial(profile, plan_name=None):
    """
    Cancel an active trial without conversion.
    Sets subscription to CANCELED and marks trial as ended.
    
    Args:
        profile: User profile
        plan_name: Optional - plan being canceled (uses subscription plan if None)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        subscription = profile.subscription
    except Subscription.DoesNotExist:
        return False, "Subscription not found"
    
    if subscription.status != SubscriptionStatus.TRIALING:
        return False, f"Subscription is not on trial (current status: {subscription.status})"
    
    # FREE_ESIGN should never be in trial status
    if subscription.plan_name == PlanName.FREE_ESIGN:
        return False, "FREE_ESIGN plan cannot have trial status (it's free for life)"
    
    current_time = now()
    trial_plan = plan_name or subscription.plan_name
    
    # Update subscription to canceled
    subscription.status = SubscriptionStatus.CANCELED
    subscription.save()
    
    # Update trial history
    try:
        trial = TrialHistory.objects.get(
            profile=profile,
            plan_name=trial_plan,
            ended_at__isnull=True
        )
        trial.ended_at = current_time
        trial.converted_to_subscription = False
        trial.save()
    except TrialHistory.DoesNotExist:
        pass
    
    return True, "Trial canceled successfully"


def check_and_expire_trials():
    """
    Check all active trials and expire them if trial period has ended.
    This should be run periodically (e.g., via a cron job or Celery task).
    Only expires trials that haven't been converted.
    
    Returns the number of trials expired.
    """
    current_time = now()
    expired_count = 0
    
    # Find all subscriptions with TRIALING status and expired trial_end
    # Exclude FREE_ESIGN (shouldn't be in trial status anyway)
    expired_subscriptions = Subscription.objects.filter(
        status=SubscriptionStatus.TRIALING,
        trial_end__lte=current_time
    ).exclude(plan_name=PlanName.FREE_ESIGN)
    
    for subscription in expired_subscriptions:
        # Use cancel_trial to properly end the trial
        success, message = cancel_trial(subscription.profile)
        if success:
            expired_count += 1
    
    return expired_count


def get_trial_status(profile):
    """
    Get the current trial status for a profile.
    
    Returns dict with trial information or None if no active trial.
    """
    try:
        subscription = profile.subscription
        
        # FREE_ESIGN is never on trial
        if subscription.plan_name == PlanName.FREE_ESIGN:
            return None
        
        if subscription.status == SubscriptionStatus.TRIALING:
            current_time = now()
            days_remaining = (subscription.trial_end - current_time).days
            hours_remaining = int((subscription.trial_end - current_time).total_seconds() / 3600)
            
            return {
                'is_trial': True,
                'plan_name': subscription.plan_name,
                'trial_start': subscription.start_date,
                'trial_end': subscription.trial_end,
                'days_remaining': max(0, days_remaining),
                'hours_remaining': max(0, hours_remaining),
                'has_expired': days_remaining < 0,
                'can_convert': True  # Always true while on trial
            }
    except Subscription.DoesNotExist:
        pass
    
    return None


def get_trial_history(profile):
    """
    Get all trial history for a profile with detailed information.
    Useful for frontend to show trial usage.
    
    Returns list of trial history dicts.
    """
    trials = TrialHistory.objects.filter(profile=profile).order_by('-started_at')
    
    history = []
    for trial in trials:
        history.append({
            'plan_name': trial.plan_name,
            'started_at': trial.started_at,
            'scheduled_end': trial.trial_end,
            'actual_end': trial.ended_at,
            'converted': trial.converted_to_subscription,
            'conversion_date': trial.conversion_date,
            'early_conversion': trial.early_conversion,
            'days_used': (trial.ended_at - trial.started_at).days if trial.ended_at else None,
        })
    
    return history


def get_trial_eligibility(profile):
    """
    Get trial eligibility status for all plans for a given profile.
    Useful for frontend to show which plans can be trialed.
    
    Returns dict with eligibility for each plan.
    """
    trial_histories = TrialHistory.objects.filter(profile=profile)
    
    has_trialed_esign = trial_histories.filter(plan_name=PlanName.ESIGN).exists()
    has_trialed_edms_plus = trial_histories.filter(plan_name=PlanName.EDMS_PLUS).exists()
    
    return {
        'FREE_ESIGN': {
            'can_trial': False,  # No trial needed, it's free
            'reason': 'No trial needed - FREE_ESIGN is free for life',
            'is_free': True
        },
        'ESIGN': {
            'can_trial': not has_trialed_esign and not has_trialed_edms_plus,
            'reason': (
                'Available for trial' if not has_trialed_esign and not has_trialed_edms_plus
                else 'Already trialed EDMS+' if has_trialed_edms_plus
                else 'Already trialed eSign'
            ),
            'has_trialed': has_trialed_esign,
            'is_free': False
        },
        'EDMS_PLUS': {
            'can_trial': not has_trialed_edms_plus,
            'reason': (
                'Available for trial' if not has_trialed_edms_plus
                else 'Already trialed EDMS+'
            ),
            'has_trialed': has_trialed_edms_plus,
            'is_free': False,
            'note': 'Can trial even after eSign trial' if has_trialed_esign and not has_trialed_edms_plus else None
        }
    }



# ----------------------------
# OTHER UTILS 
# ----------------------------


# HUMANIZE TIME
def humanize_seconds(seconds: int) -> str:
    """Convert seconds to human-readable format."""
    if seconds <= 0:
        return "expired"
    
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if sec > 0 and len(parts) == 0:  # only show seconds if no other unit
        parts.append(f"{sec} second{'s' if sec != 1 else ''}")
    return " ".join(parts)

# RANDOM USERNAME GENERATOR
def generate_unique_username(first_name, last_name):
    base = f"{first_name[0].upper()}{last_name.capitalize()}"
    username = base
    counter = 1

    while User.objects.filter(username=username).exists():
        counter += 1
        username = f"{base}{counter}"

    return username


def determine_subscription_event(subscription, previous_values):
    old_status = previous_values["status"]
    new_status = subscription.status

    old_plan = previous_values["plan_name"]
    new_plan = subscription.plan_name

    # 1️ Created
    if old_status is None:
        return SubscriptionEventType.CREATED

    # 2️ Trial Started
    if old_status != SubscriptionStatus.TRIALING and new_status == SubscriptionStatus.TRIALING:
        return SubscriptionEventType.TRIAL_STARTED

    # 3️ Activated (trial → active OR incomplete → active)
    if old_status in [
        SubscriptionStatus.TRIALING,
        SubscriptionStatus.INCOMPLETE
    ] and new_status == SubscriptionStatus.ACTIVE:
        return SubscriptionEventType.ACTIVATED

    # 4️ Reactivated (canceled → active)
    if old_status == SubscriptionStatus.CANCELED and new_status == SubscriptionStatus.ACTIVE:
        return SubscriptionEventType.REACTIVATED

    # 5️ Canceled
    if new_status == SubscriptionStatus.CANCELED:
        return SubscriptionEventType.CANCELED

    # 6️ Payment Failed
    if new_status in [
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.UNPAID
    ]:
        return SubscriptionEventType.PAYMENT_FAILED

    # 7️ Upgrade / Downgrade
    if old_plan != new_plan:
        # Define ranking logic
        plan_rank = {
            PlanName.FREE_ESIGN: 1,
            PlanName.ESIGN: 2,
            PlanName.EDMS_PLUS: 3,
        }

        if plan_rank.get(new_plan, 0) > plan_rank.get(old_plan, 0):
            return SubscriptionEventType.UPGRADED
        else:
            return SubscriptionEventType.DOWNGRADED

    # 8️ Trial Ended (trial → not trial)
    if old_status == SubscriptionStatus.TRIALING and new_status != SubscriptionStatus.TRIALING:
        return SubscriptionEventType.TRIAL_ENDED

    return SubscriptionEventType.CREATED  # safe fallback