from accounts.models import (UserAccount, AccountTier)
from django.db import transaction
import logging
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger("services")

class EmailServices:
    def __init__(self, ):
        pass

class AccountServices:
    def __init__(self, validated_data=None, id=None):
        self.data = validated_data
        self.id = id

    def create_account(self):
        if not self.data:
            logger.warning("Item not fount")
            return {"error": "Somthing went wrong"}
        
        try:
            username = self.data.get("username")
            email = self.data.get("email")
            password = self.data.get("password")

            with transaction.atomic():
                user = UserAccount.objects.create(
                    username=username,
                    email=email
                )
                user.set_password(raw_password=password)
                tier = AccountTier.objects.create(
                    account=user,
                    account_tier="free"
                )
                user.save()

                return {
                    "message": "Free tier account initiated",
                    "user": {
                        "username": user.username,
                        "date_joined": user.date_joined
                    },
                    "tier_status": {
                        "tier": tier.account_tier,
                        "limit": tier.limit,
                        "current_consuption": tier.current_count
                    }
                }
            
        except Exception as e:
            logger.warning(e)
            return {
                "error": "Somthing went wrong"
            }
    
    def deactivate_account(self):
        if not id:
            logger.warning("id not provided")

        try:
            user = UserAccount.objects.filter(id=self.id).first()
            user.is_active = False

            user.save(update_fields=["is_active"])

            return {"message": "User Deactivated"}
        
        except Exception as e:
            logger.warning(e)
            return {"error": "Something went wrong"}
        

    def login_account(self):
        username = self.data.get("username")
        password = self.data.get("password")

        try:
            user = UserAccount.objects.filter(username__iexact=username).first()

            if not user.check_password(raw_password=password):
                return {"error": "Incorrect data shared"}
            
            refresh_token = RefreshToken.for_user(user)
            access_token = refresh_token.access_token

            return {
                "message": "Login Sucessfull",
                "tokens": {
                    "refresh token": str(refresh_token),
                    "access token": str(access_token)
                }
            }
        
        except Exception as e:
            logger.warning(e)
            return {"error": e}



