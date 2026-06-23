from rest_framework import serializers
from accounts.models import UserAccount
from rest_framework.exceptions import ValidationError


class CreateAccountSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    email = serializers.EmailField()

    def validate(self, attrs):
        username = attrs.get("username")
        email = attrs.get("email")

        if not username or not email:
            raise ValidationError("Data Not provided properly")

        if UserAccount.objects.filter(username__iexact=username).exists():
            raise ValidationError("Username alredy taken")
        if UserAccount.objects.filter(email=email).exists():
            raise ValidationError("Emial alredy taken")
        
        return attrs