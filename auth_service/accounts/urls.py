"""URL configuration for authentication and license management endpoints."""

from django.urls import path
from . import views
from .views import CurrentUserView

urlpatterns = [
    # =========================
    # AUTHENTICATION ENDPOINTS
    # =========================
    path('login', views.login_view, name='login'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('register', views.register_view, name='register'),
    path('verify-email/', views.verify_email_view, name='verify-email'),
    path('resend-verification/', views.resend_verification_email_view, name='resend-verification'),
    path('password-reset/', views.password_reset_request_view, name='password-reset-request'),
    path('password-reset/confirm/', views.password_reset_confirm_view, name='password-reset-confirm'),
    path('change-password/', views.change_password_view, name='change-password'),
    path('refresh', views.refresh_view, name='refresh'),
    path('validate', views.validate_token_view, name='validate-token'),
    path('subscriptions/<str:identifier>/events/', views.list_subscription_events, name='list-subscription-events'),
    path('org/add-user', views.add_org_user_view, name='add-org-user'),


    # =========================
    # SUBSCRIPTION MANAGEMENT
    # =========================
    path('create-subscription', views.create_subscription_view, name='create-subscription'),
    path('subscription/update/stripe-subscription-id', views.update_stripe_subscription_id_view, name='update-stripe-subscription-id'),
    path('webhook/stripe-sync-subscription', views.stripe_sync_subscription_webhook, name='stripe-sync-subscription'),
    path('subscription/by-profile/<uuid:profile_id>/', views.get_subscriptions_by_profile, name='subscriptions-by-profile-id'),
    path('subscription/update-trial-billing-preference/<uuid:subscription_id>/', views.update_trial_billing_preferences_stripe, name='update-trial-billing-preferences'),
    path('subscription/<uuid:subscription_id>/cancel/', views.cancel_subscription_view, name='cancel-subscription'),
    
    
    # =========================
    # PROFILE AND SUBSCRIPTION UPDATES (Public - No Auth)
    # =========================
    path('profile/get-stripe-intent-id', views.get_stripe_intent_id_view, name='get-stripe-intent-id'),
    path('profile/update-stripe-customer', views.update_profile_stripe_customer_view, name='update-profile-stripe-customer'),

    # =========================
    # LICENSE MANAGEMENT (Admin Only)
    # =========================
    path('license/assign/<uuid:user_id>/', views.assign_license_view, name='assign-license'),
    path('license/revoke/<uuid:user_id>/', views.revoke_license_view, name='revoke-license'),
    path('license/status/', views.license_status_view, name='license-status'),
]