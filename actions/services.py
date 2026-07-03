from django.db import transaction
from actions.models import (Moniter, PingLogs, PingLogsKpis, AccountService)
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from actions.models import (AccountService)
from accounts.models import (UserAccount)
#from django_celery_beat.models import (PeriodicTask, PeriodicTasks, IntervalSchedule)
from collections import deque
import math
import logging
import requests
import time
import json


logger = logging.getLogger("services")

'''
Coexists check multiple didnt work that well.
Using TimeWheeleSchedule method
'''

class RedisTimeWheelSchedule: # Redis More flexible
    pass


from collections import deque

class CheckUser:
    def __init__(self, user: UserAccount, action: AccountService | None = None):
        self.user = user
        self.action = action

    def check_useractions(self) -> bool:
        services = AccountService.objects.filter(account=self.user)
        logger.warning(services)
        logger.warning(self.action)
        if self.action not in services:
            return False
        return True

    def check_creation(self) -> bool:
        pass

    def get_info(self) -> dict:
        data = {}
        data["created_at"] = self.action.created_at
        return data


class TimeWheelSchedule: # In memory python deque Shit Scaling Nightmare
    def __init__(self):
        self.wheel_size = 12
        self.tick_duration_mins = 5
        self.counter = 0
        self.slot = [deque() for _ in range(self.wheel_size)]

    def adition_of_task(self, action: AccountService):
        frequency = float(action.frequency_hour)
        logger.warning(frequency)
        if frequency <= 0:
            frequency = 1

        

        interval_mins = 60 // frequency
        logger.info(interval_mins)

        slot_step = max(1, interval_mins // self.tick_duration_mins)
        logger.info(slot_step)

        payload = {
            "action_id": action.id,
            "moniter": action.connection_id if action.connection_id else None,
            "url": action.url,
            "expected_status": action.expected_status,
            "remaning_laps": 0, 
            "interval_mins": interval_mins
        }
        logger.info(payload)

        target_slot = (self.counter + slot_step) % self.wheel_size
        logger.info(target_slot)

        self.slot[int(target_slot)].append(payload)
        logger.info(f"Scheduled task {action.id} to run next in Slot {target_slot} (Step: {slot_step} slots)")


    def tick(self): 
        bucket = self.slot[self.counter]
        logger.info(f"Processing Slot {self.counter}: {bucket}")

        tasks_run = []

        while bucket:
            task = bucket.popleft()
            tasks_run.append(task)

        self.slot[self.counter] = deque()

        moniter_groups = {}
        for task in tasks_run:
            moniter = task["moniter"]
            if moniter not in moniter_groups:
                moniter_groups[moniter] = []
            moniter_groups[moniter].append(task)
        
        for moniter, grouped_taks in moniter_groups.items():
            try:
                logger.info(f"Executing network checks for monitor: {moniter}")
                obj = MoniterLogServices(moniter=moniter)
                data = obj.create_logs(kpi=None)
            except Exception as e:
                logger.warning(f"Time Wheel execution error: {e}")
                data = {}

            for task in grouped_taks:
                try:
                    db_actions = AccountService.objects.get(
                        id=task["action_id"],
                        is_active=True
                    )
                    self.adition_of_task(db_actions) 
                except Exception as e:
                    logger.warning(f"Time Wheel/requeing failed: {e}")

        self.counter = (self.counter + 1) % self.wheel_size


class ActionServices:
    def __init__(self, data=None, user=None):
        self.user = user
        self.data = data
        self.default_every = 12


    def _check_and_create_action(self, action: AccountService):
        if not action:
            raise Exception()
        
        urls = action.url

        try:
            with transaction.atomic():
                moniter, created = Moniter.objects.get_or_create(
                    urls=urls,
                    frequency_hour=12,
                    is_active=True
                )

                TimeWheelSchedule().adition_of_task(action=action)

                action.connection_id = moniter
                action.save(update_fields=["connection_id"])
                return True

        except Exception as e:
            logger.warning(f"Action Service: {e}")
            return False

    def create_action(self):
        user = self.user
        urls = self.data.get("urls")
        name = self.data.get("name")
        freq = self.data.get("frequency")
        status = self.data.get("expected_status")
        is_active = self.data.get("is_active", True)

        try:
            with transaction.atomic():
                action = AccountService.objects.create(
                    account=user,
                    url=urls,
                    name=name,
                    frequency_hour=freq,
                    expected_status=status,
                    is_active=is_active
                )

                checks = self._check_and_create_action(action=action)

                if not checks:
                    transaction.set_rollback(True)
                    logger.warning(f"Checks Failed Somewhere")
                    return {
                        "error": "System failed in checks"
                    }


                return {
                    "message": "Action created Sucessfully",
                    "action": {
                        "id": action.id,
                        "name": action.name,
                        "urls": action.url,
                        "conditions": {
                            "expected_status": action.expected_status,
                            "frequency": action.frequency_hour,
                            "is_active": action.is_active
                        },
                        "dates": {
                            "created_at": action.created_at
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


    '''
    @classmethod
    def deactivate_actions(cls, pk):
        try:
            with transaction.atomic():

                moniter = Moniter.objects.get(id=pk)

                if not moniter.is_active:
                    return {"error": "Service already deactivated"}

                periodic_task = PeriodicTask.objects.filter(
                    name=f"Ping Monitor {moniter.id}"
                ).first()

                periodic_task.enabled = False
                periodic_task.save(update_fields=["enabled"])

                moniter.is_active = False
                moniter.save(update_fields=["is_active"])

                PeriodicTasks.update_changed()

                return {"message": "Deactivated successfully"}

        except Moniter.DoesNotExist:
            return {"error": "Monitor not found"}

        except Exception as e:
            logger.exception(e)
            return {"error": "Something went wrong"}
        '''



class LogsServices:
    def __init__(self, action: AccountService, user: UserAccount):
        self.action = action
        self.moniter = action.connection_id
        self.frequency = action.frequency_hour
        self.created_at = action.created_at
        self.user = user
    
    def get_logs(self):
        if not self.user:
            return None
        
        user_checks = CheckUser(user=self.user, action=self.action)

        try:
            user_data = user_checks.get_info()
            user_date_requirement = user_data.get("created_at")

            queryset_logs = PingLogs.objects.filter(moniter=self.moniter, timestamp__gt=user_date_requirement)
            return queryset_logs
        except Exception as e:
            logger.warning(e)


class MoniterLogServices:
    def __init__(self, moniter: Moniter):
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
        return True
#        return status_code == self.moniter.expected_status

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

