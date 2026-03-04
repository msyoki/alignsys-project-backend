# services/subscription_service.py

from django.db import transaction
from django.utils.timezone import now
from datetime import timedelta
from accounts.models import SubscriptionStatus


@transaction.atomic
def activate_subscription(subscription):
    """
    Marks a trial subscription as ACTIVE.
    Safe to call multiple times (idempotent).
    """

    # Idempotency guard
    if subscription.status != SubscriptionStatus.TRIALING:
        return

    subscription.status = SubscriptionStatus.ACTIVE
    subscription.billing_interval = subscription.pending_billing_interval
    subscription.no_of_licenses = subscription.pending_number_of_licenses
    subscription.current_period_end = now() + timedelta(days=30)
    subscription.trial_end = None

    subscription.save()