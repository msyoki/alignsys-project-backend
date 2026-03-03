from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [


    # Vault Objects
    path('get-vault-objects/', views.get_vault_objects, name='get_vault_objects'),
    path('update-vault-objects/', views.update_vault_objects, name='update_vault_objects'),
    path('update-specific-vault-objects/', views.update_specific_vault_objects, name='update_specific_vault_objects'),
    path('create-vault-object-permission/', views.create_vault_object_permission, name='create_vault_object_permission'),
    path('create-vault-object-permissions/', views.create_vault_object_permissions, name='create_vault_object_permissions'),
    path('get-vault-object-permissions/', views.get_vault_object_permissions, name='get_vault_object_permissions'),
    path('permissions-delete/', views.delete_permission, name='delete_permission'),
    path('list-users-without-permissions/', views.list_users_without_permissions, name='list_users_without_permissions'),
    path('update-permission/', views.update_permission, name='update_permission'),
    path('viewable-objects/', views.user_viewable_objects, name='user_viewable_objects'),

    # Vault Workflows
    path('sync-vault-workflows/', views.sync_vault_workflows, name='sync_vault_workflows'),
    path('vault/workflows/', views.get_vault_workflows, name='get_vault_workflows'),
    path('workflow/<int:workflow_id>/', views.get_workflow_by_id, name='get_workflow_by_id'),

    # Vault Users
    path('vault/users/', views.get_vault_users, name='get_vault_users'),
    
    # Permission Checks
    path('check-can-view/', views.check_can_view, name='check_can_view'),
    path('check-can-edit/', views.check_can_edit, name='check_can_edit'),
    path('check-can-delete/', views.check_can_delete, name='check_can_delete'),

    # User Groups
    path('create-user-group/', views.create_user_group, name='create_user_groupp'),


    
    # Temp file manager
    path('upload/', views.upload_temp_file, name='upload_temp_file'),
    path('files/<str:file_name>/', views.get_temp_file, name='get_temp_file'),
]
# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
