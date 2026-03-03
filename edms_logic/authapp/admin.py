from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from .models import EDMSUser, UserVaultID, UserGroup, Organization, Vault,EventLog,LoginLog
from .forms import CustomUserCreationForm,CustomUserChangeForm



class EDMSUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = EDMSUser
    list_display = ('id', 'email','username','first_name', 'last_name', 'is_staff', 'is_active', 'is_domain_user')
    list_filter = ('is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('username', 'first_name', 'last_name', 'organization', 'vaults')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_admin', 'is_domain_user', 'domain')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_active', 'is_domain_user')}
        ),
    )
    search_fields = ('email', 'first_name', 'last_name','username')
    ordering = ('email',)
    
    # This allows ManyToMany fields to be selected easily
    filter_horizontal = ('vaults',)  # 👈 This is important!



# Custom form for Organization
class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = '__all__'
        widgets = {
            'vaults': forms.CheckboxSelectMultiple,
        }

# Custom admin for Organization
class OrganizationAdmin(admin.ModelAdmin):
    form = OrganizationForm
    list_display = ('name', 'email', 'registered', 'id')

# Custom form for UserGroup
class UserGroupForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = '__all__'
        widgets = {
            'users': forms.CheckboxSelectMultiple,
        }


class VaultAdmin(admin.ModelAdmin):
    list_display = ('name', 'guid')
    search_fields = ('name', 'guid')
    

@admin.register(UserVaultID)
class UserVaultIDAdmin(admin.ModelAdmin):
    list_display = ('mfiles_id', 'vault', 'user')
    search_fields = ('mfiles_id', 'user__email', 'vault__name')
    list_filter = ('vault', 'user')

    
@admin.register(EventLog) 
class EventLogAdmin(admin.ModelAdmin): 
    list_display = ('event_id', 'event_type_value', 'category_value', 'timestamp', 'caused_by_user_login') 
    search_fields = ('event_type_value', 'category_value', 'caused_by_user_login')
    
    
    
    
@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'auth_source', 'timestamp')
    list_filter = ('auth_source', 'timestamp', 'user')
    search_fields = ('user__username', 'ip_address', 'user_agent')

# admin.site.register(UserGroup, UserGroupAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Vault, VaultAdmin)
admin.site.register(EDMSUser, EDMSUserAdmin)
