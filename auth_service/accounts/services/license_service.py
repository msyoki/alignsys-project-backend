# services/license_service.py
from django.db import transaction
from django.utils.timezone import now
from django.core.exceptions import ValidationError

class LicenseService:
    
    @staticmethod
    def get_available_licenses(profile):
        """Get number of available licenses for a profile"""
        subscription = profile.subscription
        if not subscription or subscription.status not in ['active', 'trialing']:
            return 0
        
        total_licenses = subscription.no_of_licenses
        assigned_licenses = profile.users.filter(has_license=True, is_active=True).count()
        return max(0, total_licenses - assigned_licenses)
    
    @staticmethod
    def get_assigned_licenses_count(profile):
        """Get count of currently assigned licenses"""
        return profile.users.filter(has_license=True, is_active=True).count()
    
    @staticmethod
    @transaction.atomic
    def assign_license(user):
        """Assign a license to a user"""
        profile = user.profile


         # Check 1: User already has a license
        if user.has_license:
            raise ValidationError("User already has a license")
        print(user.profile.type)
        print(user.is_admin)
        
        if not user.is_admin and user.profile.type == 'ORGANIZATION' :
            # Check 2: Subscription exists and is active
            subscription = profile.subscription
            if not subscription or subscription.status not in ['active', 'trialing']:
                raise ValidationError("No active subscription found")
            
            # Check 3: Licenses are available
            available = LicenseService.get_available_licenses(profile)
            if available <= 0:
                raise ValidationError(
                    f"No licenses available. Profile has {subscription.no_of_licenses} "
                    f"licenses and all are assigned."
                )
        
        # Assign license
        user.has_license = True
        user.license_assigned_at = now()
        user.save(update_fields=['has_license', 'license_assigned_at', 'updated_at'])
        
        return user
        
    @staticmethod
    @transaction.atomic
    def revoke_license(user):
        """Revoke a license from a user"""
        if not user.has_license:
            raise ValidationError("User does not have a license to revoke")
        
        user.has_license = False
        user.license_assigned_at = None
        user.save(update_fields=['has_license', 'license_assigned_at', 'updated_at'])
        
        return user
    
    @staticmethod
    @transaction.atomic
    def auto_assign_license_on_first_user(profile):
        """Automatically assign license to the first user of a profile"""
        if profile.users.count() == 1:
            first_user = profile.users.first()
            if not first_user.has_license:
                try:
                    LicenseService.assign_license(first_user)
                except ValidationError:
                    pass  # Silently fail if no licenses available