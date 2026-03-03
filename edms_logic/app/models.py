from django.db import models
from django.utils import timezone
from authapp.models import Vault,EDMSUser,UserGroup
from django.contrib.auth.models import Group



class FileUpload(models.Model):
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    

class Object(models.Model):
    object_id = models.IntegerField()
    name_singular = models.CharField(max_length=255)
    name_plural = models.CharField(max_length=255)
    vault = models.ForeignKey(Vault, on_delete=models.CASCADE)


    def __str__(self):
        return self.name_singular
    

class VaultObjectPermission(models.Model):
    object = models.ForeignKey(Object, on_delete=models.CASCADE)
    user = models.ForeignKey(EDMSUser, on_delete=models.CASCADE, null=True, blank=True)
    user_group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, null=True, blank=True)
    can_edit = models.BooleanField(default=False)
    can_view = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.object} Permission"
    
    
    
class Workflow(models.Model):
    name= models.CharField(max_length=200)
    vault = models.ForeignKey(Vault, on_delete=models.CASCADE)
    class_id = models.IntegerField()
    

    def __str__(self):
        return self.name
    
    
    
class State(models.Model):
    name= models.CharField(max_length=200)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    is_selected = models.BooleanField()
    

    def __str__(self):
        return self.name
    