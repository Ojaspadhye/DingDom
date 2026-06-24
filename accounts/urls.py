from rest_framework.routers import DefaultRouter
from accounts.views import (CreateAccount, DeactivateAccount, LoginAccount)

router = DefaultRouter()

router.register(prefix="accounts" , basename="account", viewset=CreateAccount)
router.register(prefix="accounts", basename="deactivate_Account", viewset=DeactivateAccount)
router.register(prefix="accounts", basename="login_account", viewset=LoginAccount)

urlpatterns = router.urls
