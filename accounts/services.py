from accounts.models import (UserAccount, AccountTier)
from django.db import transaction
import logging

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

            with transaction.atomic():
                user = UserAccount.objects.create(
                    username=username,
                    email=email
                )
                tier = AccountTier.objects.create(
                    account=user,
                    account_tier="free"
                )

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

            return {"message": "User Deactivated"}
        
        except:
            return {"error": "Something went wrong"}



