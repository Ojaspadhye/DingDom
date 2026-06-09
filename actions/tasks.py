from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from actions.models import (Moniter)
from actions.services import (MoniterLogServices)


@shared_task
def run_moniters():
    moniter_querysets = Moniter.objects.all()

    if not moniter_querysets.exists():
        print("No monitors exist.")
        return "No moniter exisit"
    
    for moniter in moniter_querysets:
        try:
            MoniterLogServices(moniter=moniter).create_logs()
        
        except ObjectDoesNotExist as e:
            print(f"Object does not exist: {e}")
        except Exception as e:
            print(f"Error executing monitor task: {e}")

    return f"{moniter_querysets.count()}"

