from django.db import models
from django.contrib.auth.models import AbstractBaseUser

# Create your models here.

class UserAccount(AbstractBaseUser):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]



class AccountTier(models.Model):
    account = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
    )
    date = models.DateField(auto_now_add=True)
    
    limit = models.IntegerField(max_length=2)
    current_count = models.IntegerField(max_length=2)

    account_tier = models.CharField(max_length=50)
