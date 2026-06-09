from rest_framework.routers import DefaultRouter
from actions.views import (
    CreateAction
)

router = DefaultRouter()

router.register(prefix="action", viewset=CreateAction, basename="actions")


urlpatterns = router.urls