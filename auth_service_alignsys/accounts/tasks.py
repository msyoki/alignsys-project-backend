from celery import shared_task
from django.utils.timezone import now
from .models import Subscription, SubscriptionStatus, PlanName
from .utils import cancel_trial  # wherever this lives
import time

@shared_task
def check_and_expire_trials():
    current_time = now()
    expired_count = 0

    expired_subscriptions = Subscription.objects.filter(
        status=SubscriptionStatus.TRIALING,
        trial_end__lte=current_time
    ).exclude(plan_name=PlanName.FREE_ESIGN)

    for subscription in expired_subscriptions:
        success, _ = cancel_trial(subscription.profile)
        if success:
            expired_count += 1

    return expired_count


# @shared_task
# def test_task():
#     print("Task started...")
#     time.sleep(5)
#     print("Task finished!")
#     return "Done"