# services/trial_scheduler.py

import requests
from django.conf import settings
from django.utils.timezone import now
from django.db import transaction

from ..models import Subscription, SubscriptionStatus
from .subscription_service import activate_subscription




def process_expired_trials():
    """
    Finds expired trial subscriptions and attempts auto activation.
    Safe to run multiple times (idempotent).
    """

    expired_trials = Subscription.objects.filter(
        status=SubscriptionStatus.TRIALING,
        trial_end__lte=now()
    ).select_related("profile")

    print(f"Found {expired_trials.count()} expired trials to process.")

    for subscription in expired_trials:
        print(f"Processing expired trial: {subscription.id}")
        print(f"Trial end: {subscription.trial_end}, Current time: {now()}")
        print(f"Pending billing interval: {subscription.pending_billing_interval}, Pending licenses: {subscription.pending_number_of_licenses}")

        # Skip if no billing preferences selected
        if not subscription.pending_billing_interval:
            continue

        # Skip if no Stripe customer
        if not subscription.profile.stripe_customer_id:
            continue

        try:
            payload = {
                "subscription_id": str(subscription.id),
                "profile_id": str(subscription.profile.id),
                "plan_name": subscription.plan_name,
                "pending_billing_interval": subscription.pending_billing_interval,
                "pending_number_of_licenses": subscription.pending_number_of_licenses,
                "stripe_customer_id": subscription.profile.stripe_customer_id,
            }

            response = requests.post(
                settings.AUTO_ACTIVATE_URL,
                json=payload,
                headers={"X-Webhook-Secret": settings.WEBHOOK_SHARED_SECRET},
                timeout=15
            )

            data = response.json()

            if response.status_code == 200 and data.get("success") is True:
                activate_subscription(subscription)

        except Exception as e:
            # Proper logging here
            print(f"Auto activation failed for {subscription.id}: {e}")