from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import EDMSUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = EDMSUser
        fields = ('email', 'first_name', 'last_name')
        widgets = {
            'vaults': forms.CheckboxSelectMultiple,
        }

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = EDMSUser
        fields = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_admin')
        widgets = {
            'vaults': forms.CheckboxSelectMultiple,
        }