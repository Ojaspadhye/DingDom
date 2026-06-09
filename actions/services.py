from django.db import transaction
from actions.models import (Moniter, PingLogs)
from django.utils import timezone
from django_celery_beat.models import (PeriodicTask, IntervalSchedule)
import logging
import requests
import time
import json


logger = logging.getLogger("services")


class ActionServices:
    @classmethod
    def create_action(cls, data):
        #user = data.get("user")
        urls = data.get("urls")
        name = data.get("name")
        freq = data.get("frequency")
        status = data.get("expected_status")
        is_active = data.get("is_active", True)

        try:
            with transaction.atomic():
                action = Moniter.objects.create(
                    urls=urls,
                    name=name,
                    frequency_hour=freq,
                    expected_status=status,
                    is_active=is_active
                )

                schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=freq,
                    period=IntervalSchedule.HOURS
                )

                PeriodicTask.objects.create(
                    interval=schedule,
                    name=f'Ping Monitor {action.id}',
                    task='actions.tasks.universal_ping_worker',
                    args=json.dumps([action.id]),
                )

            return {
                "message": "Action created Sucessfully",
                "action": {
                    "name": action.name,
                    "urls": action.urls,
                    "conditions": {
                        "expected_status": action.expected_status,
                        "frequency": action.frequency_hour,
                        "is_active": action.is_active
                    },
                    "dates": {
                        "created_at": action.created_at,
                        "last_checked": action.last_checked
                    }
                }
            }

        except ValueError as e:
            return {
                "error": e
            }
        
        except Exception as e:
            logger.warning(f"error: {e}")
            return {
                "error": "Something went wrong in sever"
            }


class LogsServices:
    @classmethod
    def get_logs(cls, moniter):
        pass


class MoniterLogServices:
    def __init__(self, moniter):
        self.moniter = moniter
        self.url = moniter.urls 

    def _send_pings(self):
        response = requests.get(url=self.url, timeout=5)
        return response
    
    def _log_pings(self, data):
        try:
            with transaction.atomic():
                PingLogs.objects.create(
                    moniter=self.moniter,
                    timestamp=data.get("timestamp"),
                    response_time=data.get("response_time"),
                    status_code=data.get("status_code"),
                    error_message=data.get("error_message"),
                    is_sucess=data.get("is_sucess")
                )

                
        except Exception as e:
            print(f"Database insertion failed: {e}")

    def _validate_sucess(self, status_code):
        return status_code == self.moniter.expected_status


    def create_logs(self):
        data = {
            "timestamp": timezone.now(),
            "response_time": None,
            "status_code": None,
            "error_message": None,
            "is_sucess": False
        }

        try:
            start_timer = time.perf_counter()
            response = self._send_pings()
            end_timer = time.perf_counter()

            data["response_time"] = (end_timer - start_timer)
            response_code = response.status_code

            data["status_code"] = response_code
            data["is_sucess"] = self._validate_sucess(response_code)
        
        except requests.exceptions.Timeout as e:
            data["error_message"] = str(e)
            data["is_sucess"] = False
        
        except requests.exceptions.ConnectionError as e:
            data["error_message"] = str(e)
            data["is_sucess"] = False
        
        except requests.exceptions.HTTPError as e:
            data["error_message"] = str(e)
            data["is_sucess"] = False
        
        except requests.exceptions.RequestException as e:
            data["error_message"] = str(e)
            data["is_sucess"] = False
        
        except Exception as e:
            data["error_message"] = f"Somthing went wrong in our system"
            data["is_sucess"] = False
            logger.warning(f"error: {e}")
        
        self._log_pings(data=data)
        return data

