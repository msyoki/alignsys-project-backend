from django.db import models

# Create your models here.

import uuid
from datetime import date
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from phone_field import PhoneField
from PIL import Image


# from django.conf import settings
# from django.db.models.signals import post_save
# from django.dispatch import receiver


class CustomAccountManager(BaseUserManager):

    def create_superuser(self, email, first_name,last_name,password, **other_fields):

        other_fields.setdefault('is_admin', True)
        other_fields.setdefault('is_superuser', True)
        other_fields.setdefault('is_active', True)
        other_fields.setdefault('avatar', "Avatars/dafault.png")

        if other_fields.get('is_admin') is not True:
            raise ValueError(
                'Superuser must be assigned to is_admin=True.')
        if other_fields.get('is_superuser') is not True:
            raise ValueError(
                'Superuser must be assigned to is_superuser=True.')

        return self.create_user(email, first_name,last_name, password, **other_fields)

    def create_user(self,email,first_name,last_name,password, **other_fields):

        if not email:
            raise ValueError(_('You must provide an email address'))

        email = self.normalize_email(email)
        user = self.model(email=email,first_name=first_name,last_name=last_name, **other_fields)
        user.set_password(password)
        user.save()
        return user

def user_directory_path(instance, filename):
    return 'Avatars/{0}'.format(filename)

def company_directory_path(instance, filename):
    return 'Company/{0}'.format(filename)

options=(
    ('Free Trial','Free Trial'),
    ('Advanced','Advanced'),
    
)

class CompanyPlan(models.Model):
    name=models.CharField(max_length=10,choices=options,primary_key=True, unique=True)
    

    def __str__(self):
        return self.name




class Company(models.Model):
    name = models.CharField(max_length=200,unique=True)
    email = models.EmailField(unique=True)
    approved = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    # Plan= models.ForeignKey(Plan,on_delete=models.CASCADE)
    logo = models.ImageField(upload_to=company_directory_path,default='Company/dafault.png')
    registered_date= models.DateTimeField(auto_now_add=True)



    class Meta:
        ordering = ['-registered_date']

    



  
    def __str__(self):
        return self.name

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=10,null=True,blank=True)
    company = models.ForeignKey(Company,on_delete=models.CASCADE, null=True,blank=True)
    avatar = models.ImageField(upload_to=user_directory_path, default='Avatars/dafault.png')
    created_date = models.DateTimeField(auto_now_add=True)
    mailtoall = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_licensed = models.BooleanField(default=False, db_column='Is_Licensed')

    @property
    def company_name(self):
        company=Company.objects.get(id=self.company)
        return company.name
    
    @property
    def getuser(self):
        user={
            "email":self.email,
            "first_name":self.first_name,
            "last_name":self.last_name
        }
        return user

    objects = CustomAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

    @property
    def is_staff(self):
        return self.is_admin


class Workflow(models.Model):
    title= models.CharField(max_length=400,db_column='title',blank=True,null=True)
    owner = models.ForeignKey(User,on_delete=models.CASCADE,db_column='owner')

    @property
    def workflowusers_emails(self):
        workflow= Workflow.objects.get(id=self.id)
        queryset2= WorkflowUser.objects.filter(workflow=workflow)

        workflowusers=[]
        for s in queryset2:
            if s.phone:
                signer={
                    "email":s.email,
                    "phone":s.phone
                }
                workflowusers.append(signer)
            else:
                signer={
                    "email":s.email
                }
                workflowusers.append(signer)
        return workflowusers

    class Meta:
        db_table='Workflow'

  
    def __str__(self):
        return f'{self.title} - {self.owner.email}'

class WorkflowUser(models.Model):
    fullname =  models.CharField(max_length=400,db_column='fullname',blank=True,null=True)
    email = models.CharField(max_length=400,db_column='email',blank=True,null=True)
    phone = models.CharField(max_length=400,db_column='phone',blank=True,null=True)
    otpverification = models.BooleanField(default=False,db_column='otpverification',blank=True,null=True)
    workflow = models.ForeignKey(Workflow,on_delete=models.CASCADE,db_column='workdlow')


    class Meta:
        db_table='WorkflowUser'

   
    def __str__(self):
        return self.fullname


class OrganizationWorkflow(models.Model):
    title= models.CharField(max_length=400,db_column='title',blank=True,null=True)
    owner = models.ForeignKey(Company,on_delete=models.CASCADE,db_column='owner')

    @property
    def workflowusers_emails(self):
        workflow= OrganizationWorkflow.objects.get(id=self.id)
        queryset2= OrganizationWorkflowUser.objects.filter(workflow=workflow)

        workflowusers=[]
        for s in queryset2:
            if s.phone:
                signer={
                    "email":s.email,
                    "phone":s.phone
                }
                workflowusers.append(signer)
            else:
                signer={
                    "email":s.email
                }
                workflowusers.append(signer)
        return workflowusers

    class Meta:
        db_table='OrganizationWorkflow'

  
    def __str__(self):
        return f'{self.title} - {self.owner.email}'

class OrganizationWorkflowUser(models.Model):
    fullname =  models.CharField(max_length=400,db_column='fullname',blank=True,null=True)
    email = models.CharField(max_length=400,db_column='email',blank=True,null=True)
    phone = models.CharField(max_length=400,db_column='phone',blank=True,null=True)
    otpverification = models.BooleanField(default=False,db_column='otpverification',blank=True,null=True)
    workflow = models.ForeignKey(OrganizationWorkflow,on_delete=models.CASCADE,db_column='workflow')


    class Meta:
        db_table='OrganizationWorkflowUser'

   
    def __str__(self):
        return self.fullname