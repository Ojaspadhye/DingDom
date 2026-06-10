from django.db import transaction
from actions.models import (Moniter, PingLogs)
from django.utils import timezone
from datetime import timedelta
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
        return PingLogs.objects.filter(moniter=moniter).order_by("-timestamp")
        


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
                ping = PingLogs.objects.create(
                    moniter=self.moniter,
                    timestamp=data.get("timestamp"),
                    response_time=data.get("response_time"),
                    status_code=data.get("status_code"),
                    error_message=data.get("error_message"),
                    is_sucess=data.get("is_sucess")
                )

                return ping

                
        except Exception as e:
            print(f"Database insertion failed: {e}")

    def _validate_sucess(self, status_code):
        return status_code == self.moniter.expected_status


    def create_logs(self):
        data = {
            "log": None,
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
        
        log = self._log_pings(data=data)
        data["log"] = log
        return data


class LogKpisServices:
    '''
    condition
    5 hr avg --> 1
    last 5 request --> 0
    '''
    def __init__(self, log, condition):
        self.log = log
        self.condition = condition

    def _get_past_queryset(self):
        moniter = self.log.moniter
        # Later user will also be added.
        # User specsific logic for get the query will be implemented
        latency_list = []

        query_set = PingLogs.objects.filter(moniter=moniter).order_by("-timestamp")

        try:
            if self.condition == 1:
                test_time = timezone.now() - timedelta(hours=5)
                for log in query_set:
                    if log.timestamp < test_time:
                        break

                    latency_list.append(log.response_time)

            elif self.condition == 0:
                for log in query_set:
                    latency_list.append(log.response_time)
        
        except Exception as e:
            logger.log(e)

        return latency_list

    def kpi_func(self):
        latency_list = self._get_past_queryset()
        
        if len(latency_list) != 0:
            return sum(latency_list) / len(latency_list)
        
        return 0



