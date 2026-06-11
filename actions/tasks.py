from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from actions.models import (Moniter)
from actions.services import (MoniterLogServices, LogKpisServices)
from django.db import transaction


@shared_task
def run_moniters():
    moniter_querysets = Moniter.objects.all()

    if not moniter_querysets.exists():
        return "No moniter exisit"
    
    for moniter in moniter_querysets:
        try:
            with transaction.atomic():
                log_data = MoniterLogServices(moniter=moniter).create_logs()
                log = log_data.get("log")
                log_timestamp = log_data.get("time_stamp")

                averages = LogKpisServices(condition=0, log=log).kpi_func()
                diff = abs(averages - log_data.get("response_time"))
                
                moniter.last_checked = log_timestamp

                log.avg_5req = averages
                log.std_5req = diff

                log.save()
                moniter.save()
        
        except ObjectDoesNotExist as e:
            print(f"Object does not exist: {e}")
        except Exception as e:
            print(f"Error executing monitor task: {e}")

    return f"{moniter_querysets.count()}"

@shared_task
def avg_per_5hr():
    moniter_queryset = Moniter.objects.all()

    if not moniter_queryset:
        return "No moniter query"
    
    for moniter in moniter_queryset:
        pass
    

