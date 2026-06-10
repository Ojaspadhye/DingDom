from rest_framework.routers import DefaultRouter
from actions.views import (
    CreateAction, GetPingLogs
)

router = DefaultRouter()

router.register(prefix="action", viewset=CreateAction, basename="actions")
router.register(prefix="logs", viewset=GetPingLogs, basename="get_logs")


urlpatterns = router.urls