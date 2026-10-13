from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from rest_framework import serializers

#https://www.django-rest-framework.org/api-guide/authentication/
#https://coffeebytes.dev/es/django-rest-framework-y-jwt-para-autenticar-usuarios/
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        print("user:",user)
        token = super().get_token(user)
        print("token:",token)

        # Add custom claims
        token['name'] = user.username
        token['rol'] = "Harristio el Simpatico"
        # ...
        print("token Ultimo:",token)
        return token


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        usuario = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return usuario