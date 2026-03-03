from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.db import models
from django.utils import timezone


# Create your models here.

class Organization(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    is_active = models.BooleanField(default=False)
    registered = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Vault(models.Model):
    guid = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    
class UserVaultID(models.Model):
    mfiles_id = models.CharField(max_length=200)
    vault = models.ForeignKey(Vault, on_delete=models.CASCADE, related_name='user_vault_id', blank=True, null=True)
    user = models.ForeignKey('EDMSUser', on_delete=models.CASCADE, related_name='user_vault_ids', blank=True, null=True)
    
    def __str__(self):
        return self.mfiles_id

class EDMSUserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, username=None):
        if not email and not username:
            raise ValueError("Either email or username must be set")

        email = self.normalize_email(email) if email else None
        user = self.model(email=email, first_name=first_name, last_name=last_name, username=username)
        user.set_password(password)
        user.is_staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, username="admin"):
        user = self.create_user(email=email, first_name=first_name, last_name=last_name, password=password, username=username)
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True

        org, _ = Organization.objects.get_or_create(name="Techedge", defaults={"email": "musyoki@techedge.co.ke"})
        user.organization = org

        user.save(using=self._db)
        return user

class EDMSUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    domain = models.CharField(max_length=50, blank=True, null=True)
    
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_domain_user = models.BooleanField(default=False)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    vaults = models.ManyToManyField(Vault, related_name='users', blank=True)

    groups = models.ManyToManyField(Group, verbose_name='groups', blank=True, related_name='users')
    user_permissions = models.ManyToManyField(Permission, verbose_name='user permissions', blank=True, related_name='users')

    objects = EDMSUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        verbose_name = "User"

    def __str__(self):
        return self.username or self.email or f"User {self.pk}"

    @property
    def getFullName(self):
        return f'{self.first_name} {self.last_name}'.strip()


    def get_user_vault_id(self, vault):
        """Retrieve the UserVaultID associated with a user and a given vault."""
        return self.user_vault_ids.filter(vault=vault).first()

class UserGroup(models.Model):
    title = models.CharField(max_length=200)
    vault = models.ForeignKey(Vault, on_delete=models.CASCADE, related_name='user_groups', blank=True, null=True)
    users = models.ManyToManyField(EDMSUser, related_name='user_groups', blank=True)

    def __str__(self):
        return self.title

class EventLog(models.Model): 
    event_id = models.IntegerField() 
    event_type_id = models.CharField(max_length=50, blank=True, null=True) 
    event_type_value = models.CharField(max_length=100, blank=True, null=True) 
    category_id = models.CharField(max_length=50, blank=True, null=True) 
    category_value = models.CharField(max_length=100, blank=True, null=True) 
    timestamp = models.DateTimeField(blank=True, null=True) 
    caused_by_user_login = models.CharField(max_length=100, blank=True, null=True) 
    caused_by_user_id = models.IntegerField(blank=True, null=True) 
    obj_type_id = models.CharField(max_length=50, blank=True, null=True) 
    obj_type_value = models.CharField(max_length=100, blank=True, null=True) 
    obj_id = models.IntegerField(blank=True, null=True) 
    obj_version = models.IntegerField(blank=True, null=True) 
    ext_id_status = models.CharField(max_length=50, blank=True, null=True) 
    ext_id_value = models.IntegerField(blank=True, null=True) 
    object_guid = models.CharField(max_length=100, blank=True, null=True) 
    version_guid = models.CharField(max_length=100, blank=True, null=True) 
    object_flag_value = models.IntegerField(blank=True, null=True) 
    object_flag_id = models.IntegerField(blank=True, null=True) 
    object_flag_value_str = models.CharField(max_length=50, blank=True, null=True) 
    original_obj_vault_value = models.CharField(max_length=100, blank=True, null=True) 
    original_obj_type = models.IntegerField(blank=True, null=True) 
    original_obj_id = models.IntegerField(blank=True, null=True) 
    title = models.CharField(max_length=100, blank=True, null=True) 
    display_id = models.IntegerField(blank=True, null=True) 
    class_id = models.IntegerField(blank=True, null=True) 
    class_value = models.CharField(max_length=100, blank=True, null=True) 
    
    class Meta: 
        verbose_name_plural = 'EventLogs' 
        def __str__(self): return f"{self.event_type_value} by {self.caused_by_user_login} at {self.timestamp}"
            
class LoginLog(models.Model):
    user = models.ForeignKey(EDMSUser, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)

    # New structured fields
    browser = models.CharField(max_length=100, blank=True, null=True)
    os = models.CharField(max_length=100, blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)  # e.g., PC, Mobile, Tablet
    platform = models.CharField(max_length=100, blank=True, null=True)    # e.g., device model if available

    auth_source = models.CharField(max_length=50, default='internal')  # internal or external
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
