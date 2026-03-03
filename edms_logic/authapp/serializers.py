# serializers.py
from rest_framework import serializers
from .models import EDMSUser,EventLog,Organization

class EDMSUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EDMSUser
        fields = ['id','username','email', 'first_name', 'last_name','is_admin', 'organization']


class EventLogSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = EventLog 
        fields = '__all__'



class EmptySerializer(serializers.Serializer):
    pass


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'email', 'is_active', 'registered']
