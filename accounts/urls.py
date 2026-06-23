from rest_framework.routers import DefaultRouter
from accounts.views import (CreateAccount)

router = DefaultRouter()

router.register(prefix="accounts" , basename="account", viewset=CreateAccount)


urlpatterns = router.urls
