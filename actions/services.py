from django.db import transaction
from actions.models import (Moniter, PingLogs, PingLogsKpis)
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
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
                    "id": action.id,
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
    
    @classmethod
    def update_action(cls, data, moniter):
        name = data.get("name")
        frequency_hour = data.get("frequency")
        expected_status = data.get("expected_status")

        try:
            if name:
                moniter.name = name
            if frequency_hour:
                moniter.frequency_hour = frequency_hour
            if expected_status:
                moniter.expected_status = expected_status
            
            return {
                "message": "Action created Sucessfully",
                "action": {
                    "name": moniter.name,
                    "urls": moniter.urls,
                    "conditions": {
                        "expected_status": moniter.expected_status,
                        "frequency": moniter.frequency_hour,
                        "is_active": moniter.is_active
                    },
                    "dates": {
                        "created_at": moniter.created_at,
                        "last_checked": moniter.last_checked
                    }
                }
            }
        
        except Exception as e:
            logger.warning(e)
            return {
                "error": "Somthing is going wrong For now"
            }



class LogsServices:
    @classmethod
    def get_logs(cls, moniter):
        try:
            logs_query_set = PingLogs.objects.filter(moniter=moniter).order_by("-timestamp")
            
            return logs_query_set
        except Exception as e:
            logger.warning(e)


class MoniterLogServices:
    def __init__(self, moniter):
        self.moniter = moniter
        self.url = moniter.urls

    def _send_pings(self):
        return requests.get(url=self.url, timeout=5)

    def _log_pings(self, data):

        try:
            with transaction.atomic():
                ping = PingLogs.objects.create(
                    moniter=self.moniter,
                    timestamp=data.get("timestamp"),
                    response_time=data.get("response_time"),
                    status_code=data.get("status_code"),
                    error_message=data.get("error_message"),
                    is_sucess=data.get("is_sucess"),
                    avg_5hr=data.get("average"),
                    std_5hr=data.get("std"),
                )
                return ping

        except Exception as e:
            print(f"Database insertion failed: {e}")
            return None

    def _validate_sucess(self, status_code):
        return status_code == self.moniter.expected_status

    def create_logs(self, kpi=None):
        data = {
            "log": None,
            "timestamp": timezone.now(),
            "response_time": 0,
            "status_code": None,
            "error_message": None,
            "is_sucess": False,
        }

        try:
            start_timer = time.perf_counter()
            response = self._send_pings()
            end_timer = time.perf_counter()

            data["response_time"] = end_timer - start_timer
            data["status_code"] = response.status_code
            data["is_sucess"] = self._validate_sucess(response.status_code)

            if kpi:
                data["average"] = kpi.average

                data["std"] = abs(kpi.average - data["response_time"])


        except requests.exceptions.RequestException as e:
            data["error_message"] = str(e)
            data["is_sucess"] = False
            data["response_time"] = time.perf_counter() - start_timer
            data["status_code"] = 0

        log = self._log_pings(data=data)
        data["log"] = log

        return data
    


## I know for now this is a Happy Path AS i dont have a catch for is missing lig and moniter but i will fix
'''
    condition
    5 hr avg --> 1
    last 5 request --> 0
'''
class LogKpisServices:
    def __init__(self, condition, log=None, moniter=None):
        self.log = log
        self.condition = condition
        self.moniter = moniter or (log.moniter if log else None)

    def _get_past_queryset(self):
        if not self.moniter:
            return 0

        if self.condition == 1:
            timespan = timezone.now() - timedelta(hours=5)

            return (
                PingLogs.objects.filter(
                    moniter=self.moniter,
                    timestamp__gte=timespan
                )
                .aggregate(avg=Avg("response_time"))["avg"]
            ) or 0

        return (
            PingLogs.objects.filter(moniter=self.moniter)
            .order_by("-timestamp")[:5]
            .aggregate(avg=Avg("response_time"))["avg"]
        ) or 0

    def kpi_func(self):
        if not self.log and not self.moniter:
            return {
                "averages": 0
            }

        averages = self._get_past_queryset()

        return {
            "averages": averages,
        }
    
    def create_ping_kpis(self):
        try:
            moniter = self.moniter
            cal_timestamp = timezone.now()
            cal_timestamp_end = timezone.now() + timedelta(minutes=5)
            average_kpis = self.kpi_func().get("averages")

            ping = PingLogsKpis.objects.create(
                moniter=moniter,
                cal_timestamp=cal_timestamp,
                average=average_kpis,
                cal_timestamp_end=cal_timestamp_end
            )

            return ping
        
        except Exception as e:
            logger.warning(e)

