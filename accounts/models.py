from django.db import models
from django.contrib.auth.models import AbstractBaseUser

# Create your models here.

class UserAccount(AbstractBaseUser):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    
    is_active = models.BooleanField(default=True) # True for now. Simple for checking. And i have added no passwords
    is_staff = models.BooleanField(default=False) # No plans of adding this yet
    
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
    
    limit = models.IntegerField(max_length=2, default=5, null=True)
    current_count = models.IntegerField(max_length=2, default=0, null=True)

    account_tier = models.CharField(max_length=50, default="free")
