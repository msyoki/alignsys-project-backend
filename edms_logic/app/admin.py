# from django.contrib import admin
# from .models import Object,VaultObjectPermission
# from django.core.exceptions import ValidationError

# class ObjectAdmin(admin.ModelAdmin):
#     list_display = ('id','object_id', 'name_singular', 'vault_name')
#     list_filter = ('vault__organization__name',)
#     search_fields = ('object_id', 'name_singular', 'vault__name', 'vault__organization__name')

#     def vault_name(self, obj):
#         return obj.vault.name if obj.vault else None

#     vault_name.short_description = 'Vault'

# class VaultObjectPermissionAdmin(admin.ModelAdmin):
#     list_display = ('id','object', 'user', 'user_group','can_edit', 'can_view', 'can_delete')
#     list_filter = ('object__vault','object__object_id',)
#     search_fields = ('object__name_singular', 'object__name_plural', 'user__username', 'user_group__name')

#     def clean(self):
#         if self.user and self.group:
#             raise ValidationError('VaultObjectPermission should be linked to either a user or a group, not both.')
#         elif not self.user and not self.group:
#             raise ValidationError('VaultObjectPermission should be linked to either a user or a group.')

# admin.site.register(VaultObjectPermission, VaultObjectPermissionAdmin)

# admin.site.register(Object, ObjectAdmin)



# # Register Vault and Organization models only if they are not already registered

