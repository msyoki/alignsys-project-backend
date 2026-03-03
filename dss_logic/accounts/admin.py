from django.contrib import admin
from accounts.models import (
    User, Company, CompanyPlan, Workflow, WorkflowUser,
    OrganizationWorkflow, OrganizationWorkflowUser
)

# User Admin already configured — just keeping search_fields optimized
class UserAdminConfig(admin.ModelAdmin):
    search_fields = ('email', 'first_name', 'last_name', 'phone', 'company__name')
    list_display = (
        'id', 'email', 'first_name', 'last_name', 
        'phone', 'company', 'is_active', 'is_admin', 
        'is_superuser', 'created_date'
    )
    list_filter = ('is_active', 'is_admin', 'is_superuser','is_licensed',  'company')
    ordering = ('-created_date',)

admin.site.register(User, UserAdminConfig)

class CompanyAdmin(admin.ModelAdmin):
    search_fields = ('name', 'email')
    list_display = ('id', 'name', 'email', 'approved', 'active', 'registered_date')
    list_filter = ('approved', 'active')
    ordering = ('-registered_date',)

admin.site.register(Company, CompanyAdmin)

class CompanyPlanAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

admin.site.register(CompanyPlan, CompanyPlanAdmin)

class WorkflowAdmin(admin.ModelAdmin):
    search_fields = ('title', 'owner__email', 'owner__first_name', 'owner__last_name')
    list_display = ('id', 'title', 'owner')
    list_filter = ('owner',)

admin.site.register(Workflow, WorkflowAdmin)

class WorkflowUserAdmin(admin.ModelAdmin):
    search_fields = ('fullname', 'email', 'phone', 'workflow__title', 'workflow__owner__email')
    list_display = ('id', 'fullname', 'email', 'phone', 'workflow', 'otpverification')
    list_filter = ('otpverification',)

admin.site.register(WorkflowUser, WorkflowUserAdmin)

class OrganizationWorkflowAdmin(admin.ModelAdmin):
    search_fields = ('title', 'owner__name', 'owner__email')
    list_display = ('id', 'title', 'owner')
    list_filter = ('owner',)

admin.site.register(OrganizationWorkflow, OrganizationWorkflowAdmin)

class OrganizationWorkflowUserAdmin(admin.ModelAdmin):
    search_fields = ('fullname', 'email', 'phone', 'workflow__title', 'workflow__owner__name')
    list_display = ('id', 'fullname', 'email', 'phone', 'workflow', 'otpverification')
    list_filter = ('otpverification',)

admin.site.register(OrganizationWorkflowUser, OrganizationWorkflowUserAdmin)
