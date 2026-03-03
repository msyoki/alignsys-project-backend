from django.urls import path
from . import views
from authapp import views as authViews
from authapp.views import MyTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

from . import views as authViews
from .views import MyTokenObtainPairView

urlpatterns = [
    # Authentication
    path('token/', MyTokenObtainPairView.as_view(), name='token_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), 
    path('vaultid/', authViews.get_user_vault_id, name='get_user_vault_id'), 
    
    

    # Organization
    path('organization/signup/', authViews.register_company_and_admin, name='new_organization_signup'), 
    path('activate/new/organization/', authViews.activate_new_organization, name='activate_org'),
    path('activate/organization/accounts/', authViews.activate_deactivated_accounts, name='activate_org_acc'),
    path('organizations/', authViews.get_organizations, name='get_organizations'),


    # User Management
    path('register/', authViews.register_user, name='register_user'),
    path('bulk-register/', authViews.bulk_register_users, name='bulk_register_users'),
    path('sync-vault-users/',authViews.sync_accounts, name='sync_vault_users'),
    path('users/organization/<int:organization_id>/', authViews.UsersByOrganizationView.as_view(), name='users-by-organization'),
    path('users-not-linked-to-vault/', authViews.users_not_linked_to_vault, name='users_not_linked_to_vault'),
    path('users-linked-to-vault/', authViews.users_linked_to_vault, name='users_linked_to_vault'),
    path('user/vaults/', authViews.user_vaults, name='user_vaults'),  
    path('assign-vault/', authViews.assign_user_to_vault, name='assign_user_to_vault'),
    path('detach-user-from-vault/', authViews.detach_user_from_vault, name='detach_user_from_vault'),
    path('password_reset/', authViews.password_reset_view, name='password_reset'),
    path('password_reset_confirm/', authViews.password_reset_confirm, name='password_reset_confirm'),

    # Logs
    path('logs/', authViews.get_logs, name='get-logs'), 
    path('logs/create/', authViews.create_log, name='create-log'), 
    path('logs/<int:event_id>/', authViews.get_log_by_id, name='get-log-by-id'),
    
    
    path('login-activity/', authViews.login_activity_post_view, name='login-activity-post-view'), 
    
    

    
    # Vault Management
    path('create-vault/', authViews.create_vault, name='create_vault'),
    path('organization-vaults/', authViews.organization_vaults, name='organization_vaults'),
    path('vault-groups/', authViews.vault_groups, name='vault_groups'),
    path('users-linked-to-vault-not-in-group/', authViews.users_linked_to_vault_not_in_group, name='users_linked_to_vault_not_in_group'),
    path('add-user-to-group/', authViews.add_user_to_group, name='add_user_to_group'),
    path('remove-user-from-group/', authViews.remove_user_from_group, name='remove_user_from_group'),
    path('remove-user-from-vault/', authViews.remove_vault_user, name='remove_user_from_vault'),
    path('add-new-vault/', authViews.register_vault, name='register_vault'),
    path('attach-existing-vault/', authViews.attach_existing_vault, name='attach_existing_vault'),
    

]
# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
