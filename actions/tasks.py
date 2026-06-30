from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from actions.models import (Moniter, PingLogsKpis, )
from actions.services import (MoniterLogServices, LogKpisServices)
from django.db import transaction
from actions.schedulers import base_wheel, global_wheel
import logging


logger = logging.getLogger(__name__)


'''
@shared_task
def run_moniters():
    moniter_querysets = Moniter.objects.all()

    if not moniter_querysets.exists():
        return "No moniter exisit"
    
    for moniter in moniter_querysets:
        if not moniter.is_active:
            break
        
        ping_kpi = None
        if PingLogsKpis.objects.filter(moniter=moniter).exists():
            ping_kpi = PingLogsKpis.objects.filter(moniter=moniter).latest("cal_timestamp")

        try:
            with transaction.atomic():
                log_data = MoniterLogServices(moniter=moniter).create_logs(kpi=ping_kpi)
                log = log_data.get("log")

                kpi_data = LogKpisServices(condition=0, log=log).kpi_func()

                log.std_5hr = abs(log_data.get("response_time") - log.avg_5hr)
                log.avg_5req = kpi_data.get("averages")
                log.std_5req = abs(log_data.get("response_time") - kpi_data.get("averages"))

                log.save()
                moniter.save()
        
        except ObjectDoesNotExist as e:
            print(f"Object does not exist: {e}")
        except Exception as e:
            print(f"Error executing monitor task: {e}")

    return f"{moniter_querysets.count()}"

    
@shared_task
def avg_per_5hr():
    if not Moniter.objects.exists():
        return "No monitors exist in the database."
    
    moniter_queryset = Moniter.objects.all().iterator()
    
    for moniter in moniter_queryset:
        try:
            kpi_service = LogKpisServices(condition=1, moniter=moniter)
            kpi_5hr = kpi_service.create_ping_kpis()
            
            if not kpi_5hr:
                print("Somthing went wrong didnt create")
                return 
            
        except Exception as e:
            print(e)
'''

@shared_task
def wheel_tick():
    try:
        if hasattr(global_wheel, "slot"):
            wheel_empty = all(len(slot) == 0 for slot in global_wheel.slot)
        else:
            wheel_empty = False
        
        if wheel_empty:
            logger.info("base_wheel implemented")
            base_wheel()


        logger.info("Wheel ticke initiated")
        global_wheel.tick()
    except Exception as e:
        logger.warning(e)

