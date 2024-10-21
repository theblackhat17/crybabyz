from rest_framework import serializers
from .models import CustomUser, Pack

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'phone', 'street', 'city', 'country', 'avatar', 'is_admin', 'is_subscribed']

class PackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pack
        fields = ['id', 'name', 'description', 'image', 'price']
