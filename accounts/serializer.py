from rest_framework import serializers
from accounts.models import UserAccount
from rest_framework.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password


class CreateAccountSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get("username")
        email = attrs.get("email")
        password = attrs.get("password")

        validate_password(password=password)

        if not username or not email:
            raise ValidationError("Data Not provided properly")

        if UserAccount.objects.filter(username__iexact=username).exists():
            raise ValidationError("Username alredy taken")
        if UserAccount.objects.filter(email=email).exists():
            raise ValidationError("Emial alredy taken")
        
        return attrs


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(min_length=8)


    def validate(self, attrs):
        username = attrs.get("username")

        if not UserAccount.objects.filter(username__iexact=username):
                raise ValidationError("user not found")
        
        return attrs