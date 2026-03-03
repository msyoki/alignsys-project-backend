"""Admin configuration for accounts app."""

from django.contrib import admin
from .models import User, Profile, Subscription, SubscriptionEvent


# ----------- Custom Filters -----------

class ProfileNameFilter(admin.SimpleListFilter):
    title = 'Profile'
    parameter_name = 'profile'

    def lookups(self, request, model_admin):
        return [(p.id, p.name) for p in Profile.objects.order_by('name')]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(profile_id=self.value())
        return queryset


class LicenseStatusFilter(admin.SimpleListFilter):
    title = 'License Status'
    parameter_name = 'license_status'

    def lookups(self, request, model_admin):
        return [
            ('licensed', 'Has License'),
            ('unlicensed', 'No License'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'licensed':
            return queryset.filter(has_license=True)
        if self.value() == 'unlicensed':
            return queryset.filter(has_license=False)
        return queryset


# ----------- User Admin -----------

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'username',
        'first_name',
        'last_name',
        'has_license',
        'license_assigned_at',
        'is_admin',
        'is_active',
        'profile',
        'profile_type',
        'id',
    )

    list_filter = (
        'is_admin',
        'is_active',
        'is_superuser',
        'has_license',
        'profile__type',
        ProfileNameFilter,
        LicenseStatusFilter,
    )

    search_fields = ('id', 'email', 'username', 'profile__name')
    ordering = ('email',)

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'last_login',
        'license_assigned_at',
    )

    fieldsets = (
        ('User ID', {'fields': ('id',)}),
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('username', 'first_name', 'last_name', 'domain')}),
        ('License', {'fields': ('has_license', 'license_assigned_at')}),
        ('Permissions', {'fields': ('is_admin', 'is_active', 'is_superuser', 'is_staff')}),
        ('Profile', {'fields': ('profile',)}),
        ('Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    def profile_type(self, obj):
        return obj.profile.type
    profile_type.short_description = 'Profile Type'


# ----------- Profile Admin -----------

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'type',
        'org_name',
        'total_users',
        'licensed_users',
        'setup_intent_id',
        'stripe_customer_id',
        'total_licenses',
        'created_at',
    )

    list_filter = ('type', 'created_at')
    search_fields = ('id', 'name', 'org_name', 'setup_intent_id', 'stripe_customer_id')

    readonly_fields = ('id', 'created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('name', 'type', 'org_name')}),
        ('Stripe', {'fields': ('setup_intent_id', 'stripe_customer_id')}),
        ('Dates', {'fields': ('created_at', 'updated_at')}),
    )

    def total_users(self, obj):
        return obj.users.count()
    total_users.short_description = 'Total Users'

    def licensed_users(self, obj):
        return obj.users.filter(has_license=True, is_active=True).count()
    licensed_users.short_description = 'Licensed Users'

    def subscription_status(self, obj):
        subscription = getattr(obj, 'subscription', None)
        return subscription.get_status_display() if subscription else 'No Subscription'
    subscription_status.short_description = 'Subscription'

    def total_licenses(self, obj):
        subscription = getattr(obj, 'subscription', None)
        return subscription.no_of_licenses if subscription else '-'
    total_licenses.short_description = 'Total Licenses'


# ----------- Subscription Admin -----------

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'plan_name',
        'status',
        'billing_interval',
        'profile',
        'license_usage',
        'start_date',
        'trial_end',
        'cancel_at',
    )

    list_filter = ('plan_name', 'status', 'billing_interval', 'created_at')
    search_fields = ('id', 'profile__name', 'stripe_subscription_id')

    readonly_fields = ('id', 'start_date', 'created_at', 'updated_at')

    fieldsets = (
        ('Subscription ID', {'fields': ('id',)}),
        ('Profile & Plan', {'fields': ('profile', 'plan_name', 'status')}),
        ('Licenses', {
            'fields': ('no_of_licenses', 'pending_number_of_licenses')
        }),
        ('Billing', {
            'fields': (
                'billing_interval',
                'pending_billing_interval',
                'stripe_subscription_id',
            )
        }),
        ('Dates', {
            'fields': (
                'start_date',
                'trial_end',
                'cancel_at',
                'cancel_at_period_end',
            )
        }),
        ('Reminders', {
            'fields': ('last_3day_reminder_sent', 'last_1day_reminder_sent')
        }),
        ('System', {'fields': ('created_at', 'updated_at')}),
    )

    def license_usage(self, obj):
        assigned = obj.profile.users.filter(has_license=True, is_active=True).count()
        return f"{assigned} / {obj.no_of_licenses}"
    license_usage.short_description = 'License Usage'


# ----------- Subscription Event Admin -----------

@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'subscription',
        'event_type',
        'created_at',
    )

    list_filter = ('event_type', 'created_at')
    search_fields = ('id', 'subscription__id', 'subscription__profile__name')

    readonly_fields = ('id', 'created_at')

    fieldsets = (
        ('Event ID', {'fields': ('id',)}),
        ('Details', {'fields': ('subscription', 'event_type', 'metadata')}),
        ('System', {'fields': ('created_at',)}),
    )