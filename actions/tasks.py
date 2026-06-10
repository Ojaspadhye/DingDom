from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from actions.models import (Moniter)
from actions.services import (MoniterLogServices, LogKpisServices)


@shared_task
def run_moniters():
    moniter_querysets = Moniter.objects.all()

    if not moniter_querysets.exists():
        return "No moniter exisit"
    
    for moniter in moniter_querysets:
        try:
            log_data = MoniterLogServices(moniter=moniter).create_logs()
            log = log_data.get("log")
            averages = LogKpisServices(condition=0, log=log).kpi_func()
            diff = abs(averages - log_data.get("response_time"))
            log.avg_5req = averages
            log.std_5req = diff
            log.save()
        
        except ObjectDoesNotExist as e:
            print(f"Object does not exist: {e}")
        except Exception as e:
            print(f"Error executing monitor task: {e}")

    return f"{moniter_querysets.count()}"

