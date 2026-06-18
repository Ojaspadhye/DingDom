from rest_framework.routers import DefaultRouter
from actions.views import (
    CreateAction, UpdateAction,
    GetPingLogs, DeactivateAction
)

router = DefaultRouter()

# Actions
router.register(prefix="action", viewset=CreateAction, basename="create_actions")
router.register(prefix="action", viewset=UpdateAction, basename="update_actions")
router.register(prefix="action", viewset=DeactivateAction, basename="deactivate_action")

# Logs
router.register(prefix="logs", viewset=GetPingLogs, basename="get_logs")


urlpatterns = router.urls