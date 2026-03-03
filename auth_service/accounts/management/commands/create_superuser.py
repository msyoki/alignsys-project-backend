"""Management command to create a superuser."""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError
from accounts.models import Profile, UserType, Subscription, PlanName, SubscriptionStatus, BillingInterval
from accounts.utils import generate_unique_username
from accounts.services.license_service import LicenseService

User = get_user_model()

class Command(BaseCommand):
    help = "Create a superuser for the application"
    
    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, help="Email address")
        parser.add_argument("--password", type=str, help="Password")
        parser.add_argument("--first_name", type=str, help="First name")
        parser.add_argument("--last_name", type=str, help="Last name")
    
    @transaction.atomic
    def handle(self, *args, **options):
        email = options.get("email") or input("Email: ").strip()
        password = options.get("password") or input("Password: ").strip()
        first_name = options.get("first_name") or input("First name: ").strip()
        last_name = options.get("last_name") or input("Last name: ").strip()
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f"User with email {email} already exists")
            )
            return
        
        # Generate unique username
        username = generate_unique_username(first_name, last_name)
        
        try:
            # Create profile
            profile = Profile.objects.create(
                name="Alignsys Corp",
                type=UserType.ORGANIZATION,
                org_name="System",
            )
            self.stdout.write(self.style.SUCCESS(f"Created profile: {profile.name}"))
            
            # Create default subscription for the profile
            subscription = Subscription.objects.create(
                profile=profile,
                plan_name=PlanName.EDMS_PLUS,
                status=SubscriptionStatus.ACTIVE,
                no_of_licenses=5,
                billing_interval=BillingInterval.NONE
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created subscription: {subscription.plan_name} with {subscription.no_of_licenses} licenses"
                )
            )
            
            # Create superuser
            new_user = User.objects.create_superuser(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                profile=profile,
            )
            self.stdout.write(self.style.SUCCESS(f"Created superuser: {email}"))
            
            # Assign license to superuser
            try:
                LicenseService.assign_license(new_user)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ License assigned to {email}")
                )
            except ValidationError as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to assign license: {str(e)}")
                )
                # Since we're in a transaction, this will rollback everything
                raise
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{'='*60}\n"
                    f"Successfully created superuser!\n"
                    f"Email: {email}\n"
                    f"Profile: {profile.name}\n"
                    f"Subscription: {subscription.plan_name}\n"
                    f"Licenses: {subscription.no_of_licenses}\n"
                    f"License Assigned: Yes\n"
                    f"{'='*60}\n"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating superuser: {str(e)}")
            )
            raise