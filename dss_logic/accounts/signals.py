from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from models import Logs
from .utilities import get_client_ip
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

@receiver(user_logged_in)
def log_user_login(sender,user, request, **kwargs):
    if not user.is_superuser:
        IPAddr = get_client_ip(request) 
        full_name= f"{request.user.first_name} {request.user.last_name}"
        Logs.objects.create(user_email=request.user.email,ip_address=IPAddr,activity="login",name=full_name)
	

# @receiver(user_login_failed)
# def log_user_login_failed(sender,credentials,request,**kwargs):
#     IPAddr = get_client_ip(request)    
#     Logs.objects.create(user_email=credentials['username'],ip_address=IPAddr,activity="Failed login",)
    

# @receiver(user_logged_out)
# def log_user_logout(sender,user, request, **kwargs):
#     if not user.is_superuser and not user.is_admin:
#         IPAddr = get_client_ip(request)  
#         full_name= f"{request.user.first_name} {request.user.last_name}"
#         Logs.objects.create(user_email=request.user.email,ip_address=IPAddr,activity="logout",user_name=full_name)
        

