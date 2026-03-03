"""URL configuration for user management endpoints."""
from django.urls import path
from . import user_views

urlpatterns = [
    path('profile/<str:profile_id>', user_views.get_profile, name='get-profile'),
    path('', user_views.get_all_users, name='all-users'),
]
