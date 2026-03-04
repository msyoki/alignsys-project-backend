from django.core.management.base import BaseCommand
from accounts.services.trial_scheduler import process_expired_trials


class Command(BaseCommand):
    help = "Process expired trial subscriptions"

    def handle(self, *args, **kwargs):
        self.stdout.write("Checking expired trials...")
        process_expired_trials()
        self.stdout.write(self.style.SUCCESS("Done processing trials."))