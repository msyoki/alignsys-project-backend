from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.forms import AuthenticationForm, UsernameField, PasswordResetForm, SetPasswordForm
from accounts.models import User
from django.contrib.auth import (
    password_validation,
)


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='*New password',
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'password',
                'class': 'form-control form-control-md',
                'placeholder':'password'
            }),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )

    password2 = forms.CharField(
        label='Password confirm',
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'password',
                'class': 'form-control form-control-md',
                'placeholder':'confirm password'
            }),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )

    first_name = forms.CharField(
        label='First Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-md',
                'placeholder':'first name'
            }
        ),
        
    )
   
    last_name = forms.CharField(
        label='Last Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-md',
                'placeholder':'last name'
            }
        ),
            
    )
    
    phone_number = forms.CharField(
        label='Phone Number',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-md',
                'pattern':"[2]{1}[5]{1}[4]{1}[1-7]{1}[0-9]{2}[0-9]{3}[0-9]{3}",
                'placeholder':'254xxx-xxx-xxx'
            }
        ),
        
    )

    email = forms.EmailField(
        label='*Email Address',
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                'autocomplete': 'email',
                'class': 'form-control form-control-md',
                'placeholder':'email address'
            }   
        )
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name','phone_number')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name',
                  'is_active', 'is_admin',)

    def clean_password(self):
        return self.initial["password"]

class CustomAuthenticationForm(AuthenticationForm):
    username = UsernameField(
        label='Email/Phone Number',
        widget=forms.TextInput(
            attrs={
                'placeholder': 'email/phone number',
                'class': 'form-control form-control-md '
            }
        )
    )

    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'password',
                'class': 'form-control form-control-md '
            }
        )
    )

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label='*Email Address',
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                'autocomplete': 'email',
                'class': 'form-control form-control-md bg-light'
            })
    )

class CustomPasswordResetConfirmForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label='*New password',
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'new-password',
                'autocomplete': 'email',
                'class': 'form-control form-control-md bg-light'
            }),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label='*New password confirmation',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'new-password',
                'autocomplete': 'email',
                'class': 'form-control form-control-md bg-light'
            }),
    )

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name' , 'avatar']