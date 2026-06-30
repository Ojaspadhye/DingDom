from actions.services import TimeWheelSchedule
from actions.models import AccountService


global_wheel = TimeWheelSchedule()

def base_wheel():
    active_demand = AccountService.objects.filter(is_active=True).select_related("connection_id")
    for action in active_demand:
        global_wheel.adition_of_task(action=action)
