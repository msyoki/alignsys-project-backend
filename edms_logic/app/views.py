import base64
import os
import time
from pathlib import Path
from threading import Thread

import mimetypes
import requests
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Vault, Object, VaultObjectPermission, Workflow, State
from .serializers import FileUploadSerializer
from authapp.models import Organization, EDMSUser, UserGroup

# Constants
TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(exist_ok=True)
FILE_RETENTION_TIME = 120
PERMISSION_FIELDS = ['can_edit', 'can_view', 'can_delete']

# Ensure base_url is defined (should be in settings)
base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')


# Helper Functions
def create_error_response(message, status_code=status.HTTP_400_BAD_REQUEST, extra_data=None):
    """Create standardized error response"""
    data = {'error': message}
    if extra_data:
        data.update(extra_data)
    return Response(data, status=status_code)


def create_success_response(message, status_code=status.HTTP_200_OK, extra_data=None):
    """Create standardized success response"""
    data = {'message': message}
    if extra_data:
        data.update(extra_data)
    return Response(data, status=status_code)


def get_user_permission(user, object_instance):
    """Get user permission for an object, checking both direct and group permissions"""
    # Check direct user permission
    user_permission = VaultObjectPermission.objects.filter(
        user=user, object=object_instance
    ).first()
    
    if user_permission:
        return user_permission
    
    # Check group permissions
    user_groups = user.user_groups.all()
    group_permission = VaultObjectPermission.objects.filter(
        user_group__in=user_groups, object=object_instance
    ).first()
    
    return group_permission


def delete_file_after_delay(file_path: Path) -> None:
    """Delete the file after a specified delay."""
    time.sleep(FILE_RETENTION_TIME)
    try:
        file_path.unlink()
        print(f"Deleted file: {file_path}")
    except OSError as e:
        print(f"Error deleting file: {e}")


def clean_base64_content(base64_content: str) -> str:
    """Remove the data URI prefix if present."""
    if not base64_content.startswith('data:'):
        return base64_content
    return base64_content.split(',', 1)[1]


# File Upload Views
@api_view(['POST'])
def upload_temp_file(request):
    """Endpoint to upload a file via Base64 content."""
    serializer = FileUploadSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Decode base64 data
        base64_data = clean_base64_content(serializer.validated_data['base64_content'])
        file_data = base64.b64decode(base64_data)
    except Exception as e:
        print(f"Base64 decoding error: {e}")
        return create_error_response("Invalid Base64 content.", extra_data={'error': str(e)})

    try:
        # Save file
        file_extension = serializer.validated_data['file_extension']
        file_name = f"{int(time.time())}.{file_extension}"
        file_path = TEMP_DIR / file_name
        
        file_path.write_bytes(file_data)
        
        # Schedule file deletion
        Thread(target=delete_file_after_delay, args=(file_path,), daemon=True).start()
        
        return Response({"url": f"/files/{file_name}"}, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error while saving the file: {e}")
        return create_error_response("Failed to save the file.", 
                                   status.HTTP_500_INTERNAL_SERVER_ERROR,
                                   extra_data={'error': str(e)})


def get_temp_file(file_name):
    """Endpoint to retrieve the uploaded file."""
    file_path = TEMP_DIR / file_name
    
    if not file_path.exists():
        return create_error_response("File not found.", 
                                   status.HTTP_404_NOT_FOUND,
                                   extra_data={'file_name': file_name})

    try:
        with open(file_path, 'rb') as file:
            file_data = file.read()
        return Response(file_data, content_type='application/octet-stream')
        
    except Exception as e:
        print(f"Error reading the file: {e}")
        return create_error_response("Error reading the file.",
                                   status.HTTP_500_INTERNAL_SERVER_ERROR,
                                   extra_data={'error': str(e)})


# Permission Views
@api_view(['POST'])
def get_vault_object_permissions(request):
    """Get permissions for a specific vault object."""
    object_id = request.data.get('object_id')
    vault_guid = request.data.get('vault_guid')
    
    if object_id is None or vault_guid is None:
        return create_error_response('Both object_id and vault_guid are required in the request body')

    try:
        vault = get_object_or_404(Vault, guid=vault_guid)
        obj = get_object_or_404(Object, object_id=object_id, vault=vault)
        
        permissions = VaultObjectPermission.objects.filter(object=obj).select_related('user', 'user_group')
        
        serialized_permissions = []
        for permission in permissions:
            name = "Unknown"
            if permission.user:
                name = f'{permission.user.first_name} {permission.user.last_name}'
            elif permission.user_group:
                name = permission.user_group.title
                
            serialized_permissions.append({
                'id': permission.id,
                'name': name,
                'can_edit': permission.can_edit,
                'can_view': permission.can_view,
                'can_delete': permission.can_delete
            })

        return Response(serialized_permissions, status=status.HTTP_200_OK)
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_vault_objects(request):
    """Get all objects for a specific vault."""
    guid = request.data.get('guid')
    if not guid:
        return create_error_response('GUID not provided in request body')
    
    try:
        vault = get_object_or_404(Vault, guid=guid)
        objects = Object.objects.filter(vault=vault)
        
        serialized_objects = [{
            'object_id': obj.object_id,
            'name_singular': obj.name_singular,
            'name_plural': obj.name_plural
        } for obj in objects]
        
        return Response(serialized_objects, status=status.HTTP_200_OK)
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_vaults(request):
    """Get vaults from external API."""
    try:
        url = f"{base_url}/api/Vaults/Techedge"
        response = requests.get(url)

        if response.status_code == 200:
            return create_success_response('Accounts activated successfully.')
        else:
            return create_error_response('Failed to register organization vault')
    
    except Organization.DoesNotExist:
        return create_error_response('Organization does not exist.')


def update_vault_objects_helper(vault):
    """Helper function to update objects for a single vault."""
    response = requests.get(f'{base_url}/api/MfilesObjects/GetVaultsObjects/{vault.guid}')
    
    if response.status_code != 200:
        return False, f'Failed to fetch objects for vault {vault.guid}. Status code: {response.status_code}'
    
    data = response.json()
    received_object_ids = {item['objectid'] for item in data}

    # Get existing objects
    existing_objects = Object.objects.filter(vault=vault)
    
    # Delete objects not in the response
    objects_to_delete = existing_objects.exclude(object_id__in=received_object_ids)
    objects_to_delete.delete()

    # Create or update objects
    for item in data:
        Object.objects.update_or_create(
            object_id=item['objectid'],
            vault=vault,
            defaults={
                'name_singular': item['namesingular'],
                'name_plural': item['nameplural'],
            }
        )
    
    return True, None


@api_view(['POST'])
def update_specific_vault_objects(request):
    """Update objects for a specific vault."""
    guid = request.data.get('guid')
    
    if not guid:
        return create_error_response('No GUID provided')
    
    try:
        vault = get_object_or_404(Vault, guid=guid)
        success, error = update_vault_objects_helper(vault)
        
        if success:
            return create_success_response('Vault objects updated successfully')
        else:
            return create_error_response(error, status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def update_vault_objects(request):
    """Update objects for all vaults."""
    try:
        vaults = Vault.objects.all()
        
        for vault in vaults:
            update_vault_objects_helper(vault)
        
        return create_success_response('Vault objects updated successfully')
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


def check_permission_helper(email, object_id, vault_guid, permission_type):
    """Helper function for permission checking."""
    try:
        user = EDMSUser.objects.get(email=email)
        object_instance = Object.objects.get(object_id=object_id, vault__guid=vault_guid)
        
        permission = get_user_permission(user, object_instance)
        
        if permission:
            return getattr(permission, permission_type, False)
        return False
        
    except EDMSUser.DoesNotExist:
        raise ValueError('User not found')
    except Object.DoesNotExist:
        raise ValueError('Object not found')


@api_view(['POST'])
def check_can_view(request):
    """Check if user can view an object."""
    try:
        email = request.data.get('email')
        object_id = request.data.get('object_id')
        vault_guid = request.data.get('vault_guid')
        
        can_view = check_permission_helper(email, object_id, vault_guid, 'can_view')
        return Response({'can_view': can_view}, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return create_error_response(str(e), status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def check_can_edit(request):
    """Check if user can edit an object."""
    try:
        email = request.data.get('email')
        object_id = request.data.get('object_id')
        vault_guid = request.data.get('vault_guid')
        
        can_edit = check_permission_helper(email, object_id, vault_guid, 'can_edit')
        return Response({'can_edit': can_edit}, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return create_error_response(str(e), status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def check_can_delete(request):
    """Check if user can delete an object."""
    try:
        email = request.data.get('email')
        object_id = request.data.get('object_id')
        vault_guid = request.data.get('vault_guid')
        
        can_delete = check_permission_helper(email, object_id, vault_guid, 'can_delete')
        return Response({'can_delete': can_delete}, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return create_error_response(str(e), status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def create_vault_object_permission(request):
    """Create a new vault object permission."""
    user_id = request.data.get('user_id')
    group_id = request.data.get('group_id')
    object_id = request.data.get('object_id')
    can_edit = request.data.get('can_edit')
    can_view = request.data.get('can_view')
    can_delete = request.data.get('can_delete')

    # Validation
    if not user_id and not group_id:
        return create_error_response('Either user_id or group_id must be provided.')
    if user_id and group_id:
        return create_error_response('Provide only one of user_id or group_id, not both.')

    try:
        object_instance = get_object_or_404(Object, object_id=object_id)
        
        vault_object_permission = VaultObjectPermission(
            object=object_instance,
            can_edit=can_edit,
            can_view=can_view,
            can_delete=can_delete
        )

        if user_id:
            user = get_object_or_404(EDMSUser, id=user_id)
            vault_object_permission.user = user
        elif group_id:
            group = get_object_or_404(UserGroup, id=group_id)
            vault_object_permission.user_group = group

        vault_object_permission.save()
        return create_success_response('VaultObjectPermission created successfully', 
                                     status.HTTP_201_CREATED)
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


# Group Management Views
@api_view(['POST'])
def create_user_group(request):
    """Create a new user group."""
    title = request.data.get('title')
    vault_id = request.data.get('vault')
    user_ids = request.data.get('users', [])

    if not title:
        return create_error_response('Title is required')
    
    try:
        vault = get_object_or_404(Vault, id=vault_id) if vault_id else None
        users = EDMSUser.objects.filter(id__in=user_ids) if user_ids else []

        user_group = UserGroup.objects.create(title=title, vault=vault)
        
        if users.exists():
            user_group.users.set(users)

        return create_success_response('User group created successfully',
                                     status.HTTP_201_CREATED,
                                     extra_data={'user_group_id': user_group.id})
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def add_users_to_group(request):
    """Add users to an existing group."""
    group_id = request.data.get('group_id')
    user_ids = request.data.get('user_ids', [])

    if not group_id:
        return create_error_response('Group ID is required')
    if not user_ids:
        return create_error_response('User IDs are required')

    try:
        user_group = get_object_or_404(UserGroup, id=group_id)
        users = EDMSUser.objects.filter(id__in=user_ids)
        
        user_group.users.add(*users)
        return create_success_response('Users added to the group successfully')
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def remove_user_from_group(request):
    """Remove a user from a group."""
    group_id = request.data.get('group_id')
    user_id = request.data.get('user_id')

    if not group_id:
        return create_error_response('Group ID is required')
    if not user_id:
        return create_error_response('User ID is required')

    try:
        user_group = get_object_or_404(UserGroup, id=group_id)
        user = get_object_or_404(EDMSUser, id=user_id)
        
        user_group.users.remove(user)
        return create_success_response('User removed from the group successfully')
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def delete_permission(request):
    """Delete a vault object permission."""
    permission_id = request.data.get('permission_id')
    
    try:
        permission = get_object_or_404(VaultObjectPermission, pk=permission_id)
        permission.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def list_users_without_permissions(request):
    """List users and groups without permissions for a specific vault object."""
    vault_guid = request.data.get('vault_guid')
    object_id = request.data.get('object_id')
    
    if not vault_guid or object_id is None:
        return create_error_response('vault_guid and object_id are required.')
    
    try:
        vault = get_object_or_404(Vault, guid=vault_guid)
        object_instance = get_object_or_404(Object, object_id=object_id, vault=vault)
        
        # Get users without permissions
        users_without_permissions = EDMSUser.objects.filter(
            organization=vault.organization
        ).exclude(
            vaultobjectpermission__object=object_instance
        ).distinct()

        # Get user groups without permissions
        user_groups_without_permissions = UserGroup.objects.filter(
            organization=vault.organization
        ).exclude(
            vaultobjectpermission__object=object_instance
        ).distinct()
        
        users_data = [
            {'id': user.id, 'name': f'{user.first_name} {user.last_name}'}
            for user in users_without_permissions
        ]
        user_groups_data = [
            {'id': group.id, 'title': group.title}
            for group in user_groups_without_permissions
        ]
        
        return Response({
            'users': users_data,
            'user_groups': user_groups_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_vault_object_permissions(request):
    """Create vault object permissions for multiple users and groups."""
    vault_guid = request.data.get('vault_guid')
    object_id = request.data.get('object_id')
    selected_users = request.data.get('selectedUsers', [])
    selected_groups = request.data.get('selectedGroups', [])

    try:
        vault = get_object_or_404(Vault, guid=vault_guid)
        object_instance = get_object_or_404(Object, object_id=object_id, vault=vault)

        # Create permissions for selected users
        for user_id in selected_users:
            user = get_object_or_404(EDMSUser, id=user_id)
            VaultObjectPermission.objects.update_or_create(
                object=object_instance,
                user=user,
                defaults={'can_view': True, 'can_edit': True, 'can_delete': True}
            )

        # Create permissions for selected groups
        for group_id in selected_groups:
            group = get_object_or_404(UserGroup, id=group_id)
            VaultObjectPermission.objects.update_or_create(
                object=object_instance,
                user_group=group,
                defaults={'can_view': True, 'can_edit': True, 'can_delete': True}
            )

        return create_success_response('VaultObjectPermissions created or updated successfully')
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def update_permission(request):
    """Update a specific permission field."""
    instance_id = request.data.get('id')
    field_name = request.data.get('field')
    new_value = request.data.get('value')

    # Validation
    if not instance_id or not field_name or new_value is None:
        return create_error_response('Missing id, field, or value in request body')
    
    if field_name not in PERMISSION_FIELDS:
        return create_error_response('Invalid field name')

    try:
        permission_instance = get_object_or_404(VaultObjectPermission, id=instance_id)
        setattr(permission_instance, field_name, new_value)
        permission_instance.save()
        
        return create_success_response('Field updated successfully')
        
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_viewable_objects(request):
    """Get all objects the authenticated user can view."""
    try:
        user = request.user

        # Get direct permissions
        direct_permissions = VaultObjectPermission.objects.filter(
            user=user, can_view=True
        ).values_list('object__object_id', flat=True)

        # Get group permissions
        user_groups = user.user_groups.all()
        group_permissions = VaultObjectPermission.objects.filter(
            user_group__in=user_groups, can_view=True
        ).values_list('object__object_id', flat=True)

        # Combine permissions
        viewable_object_ids = set(direct_permissions).union(set(group_permissions))

        return Response(list(viewable_object_ids), status=status.HTTP_200_OK)

    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


# Workflow Views
@api_view(['POST'])
def sync_vault_workflows(request):
    """Sync workflows for a specific vault from external API."""
    vault_guid = request.data.get('guid')
    vault = get_object_or_404(Vault, guid=vault_guid)

    url = f'{base_url}/api/WorkflowsInstance/GetVaultsWorkflows/{vault_guid}'
    headers = {'accept': '*/*'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        workflows_data = response.json()

        # Clean up if no workflows
        if not workflows_data:
            Workflow.objects.filter(vault=vault).delete()
            return create_success_response("No workflows associated with this vault. Database cleaned up.")

        # Process workflows
        for workflow_data in workflows_data:
            workflow_id = workflow_data['workflowId']
            workflow_name = workflow_data['workflowName']
            class_id = workflow_data['classId']
            states_data = workflow_data['states']

            # Update or create workflow
            workflow, created = Workflow.objects.update_or_create(
                id=workflow_id,
                vault=vault,
                defaults={'name': workflow_name, 'class_id': class_id}
            )

            # Process states
            existing_states = {state.name: state for state in State.objects.filter(workflow=workflow)}
            
            for state_data in states_data:
                state_id = state_data['stateId']
                state_name = state_data['stateName']
                is_selectable = state_data['isSelectable']

                State.objects.update_or_create(
                    id=state_id,
                    workflow=workflow,
                    defaults={'name': state_name, 'is_selected': is_selectable}
                )

                existing_states.pop(state_name, None)

            # Remove obsolete states
            for state in existing_states.values():
                state.delete()

        return create_success_response("Workflows and states have been synced successfully.")

    except requests.RequestException as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_vault_workflows(request):
    """Get all workflows for a specific vault."""
    guid = request.data.get("guid")
    vault = get_object_or_404(Vault, guid=guid)
    
    workflows = Workflow.objects.filter(vault=vault).prefetch_related('state_set')
    
    workflows_data = []
    for workflow in workflows:
        workflow_data = {
            'workflowId': workflow.id,
            'workflowName': workflow.name,
            'classId': workflow.class_id,
            'states': [
                {
                    'stateId': state.id,
                    'stateName': state.name,
                    'isSelectable': state.is_selected
                }
                for state in workflow.state_set.all()
            ]
        }
        workflows_data.append(workflow_data)
    
    return Response(workflows_data)


@api_view(['GET'])
def get_workflow_by_id(request, workflow_id):
    """Get a specific workflow by ID."""
    workflow = get_object_or_404(Workflow, id=workflow_id)
    
    workflow_data = {
        'workflowId': workflow.id,
        'workflowName': workflow.name,
        'classId': workflow.class_id,
        'states': [
            {
                'stateId': state.id,
                'stateName': state.name,
                'isSelectable': state.is_selected
            }
            for state in workflow.state_set.all()
        ]
    }
    
    return Response(workflow_data)


@api_view(['POST'])
def get_vault_users(request):
    """Get all users associated with a specific vault."""
    guid = request.data.get('vault_id')
    
    try:
        vault = get_object_or_404(Vault, guid=guid)
        
        users = EDMSUser.objects.filter(
            user_groups__vault=vault
        ).distinct().values('id', 'first_name', 'last_name', 'email')

        return Response(list(users), status=status.HTTP_200_OK)

    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def get_organizations(request):
    """Get all organizations."""
    try:
        organizations = Organization.objects.all().values('id', 'name')
        return Response(list(organizations), status=status.HTTP_200_OK)
    except Exception as e:
        return create_error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)