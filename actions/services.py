from django.db import transaction
from actions.models import (Moniter, PingLogs, PingLogsKpis, AccountService, ServiceDeactivation)
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from accounts.models import (UserAccount)
from django.db.models.functions import ExtractMinute
from django.db.models.functions import ExtractMinute, Mod
from django.db.models import Value
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


def get_workable_range(action: AccountService):
    query_set = ServiceDeactivation.objects.filter(action=action).order_by("created_at")

    working_ranges = [
        (action.created_at, None)
    ]

    if not query_set.exists():
        return working_ranges

    working_ranges[0] = (
        action.created_at,
        query_set.first().created_at
    )

    start = None

    for item in query_set:
        if item.is_Activation:
            start = item.created_at
        elif start is not None:
            working_ranges.append((start, item.created_at))
            start = None

    if start is not None:
        working_ranges.append((start, None))

    logger.info(working_ranges)
    return working_ranges

class RedisTimeWheelSchedule: # Redis More flexible
    pass


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
        data["frequency"] = self.action.frequency_hour

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
    

    def purge_task(self, action: AccountService):
        frequency = float(action.frequency_hour)
        interval_mins = 60 // frequency

        payload = {
            "action_id": action.id,
            "moniter": action.connection_id if action.connection_id else None,
            "url": action.url,
            "expected_status": action.expected_status,
            "remaning_laps": 0,
            "interval_mins": interval_mins
        }

        for bucket in self.slot:
            try:
                while True:
                    try:
                        bucket.remove(payload)
                    except ValueError:
                        break
                    except Exception as e:
                        logger.warning(e)
                        break


            except ValueError:
                continue
            except Exception as e:
                logger(e)


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
        
    def _update_frequency(self, action: AccountService, frequency) -> bool:
        try:
            obj = TimeWheelSchedule()

            purge = obj.purge_task(action=action)
            insert_update = obj.adition_of_task(action=action)

            return True


        except Exception as e:
            logger.warning(e)
            return False

    
    def update_action(self, action: AccountService):
        name = self.data.get("name")
        frequency_hour = self.data.get("frequency")
        expected_status = self.data.get("expected_status")

        try:
            if name:
                action.name = name

            if frequency_hour:
                action.frequency_hour = frequency_hour
                updated_frequency_response = self._update_frequency(action=action, frequency=frequency_hour)
                
                if not updated_frequency_response:
                    return {"error": "frequency_hour failed to updae"}

            if expected_status:
                action.expected_status = expected_status
            
            logger.warning("Saving so it failes worng there ")
            
            action.save()
            
            return {
                "message": "Action created Sucessfully",
                "action": {
                    "name": action.name,
                    "urls": action.url,
                    "conditions": {
                        "expected_status": action.expected_status,
                        "frequency": action.frequency_hour,
                        "is_active": action.is_active
                    },
                    "dates": {
                        "created_at": action.created_at,
                        "last_checked": action.connection_id.last_checked
                    }
                }
            }
        
        except Exception as e:
            logger.warning(e)
            return {
                "error": "Somthing is going wrong For now"
            }


    def _deactivate_actions(self, action: AccountService):
        action_url = action.url
        action_id = action.id
        connection = action.connection_id

        try:
            with transaction.atomic():
                if not AccountService.objects.filter(url=action_url).exclude(id=action_id).exists():
                    connection.is_active = False
                    connection.save(update_fields=["is_active"])

                obj = TimeWheelSchedule()

                purge = obj.purge_task(action=action)
                action.is_active = False

                action.save(update_fields=["is_active"])

                ServiceDeactivation.objects.create(
                    action=action,
                    is_Activation=False
                )

                logger.info(f"{action_id} is purged completly")
                return True
        
        except Exception as e:
            logger.warning(f"This is in _deactivation: {e}")
            return False
    

    def deactivate_actions(self, pk):
        if not AccountService.objects.filter(id=pk).exists():
            return {"error": "object Dose not exist"}
        
        action = AccountService.objects.get(id=pk)

        try:
            is_deactivated = self._deactivate_actions(action=action)

            if is_deactivated:
                return {"message": "service deactivated"}
            
            return {"error": "Deactivation Failed"}
        except Exception as e:
            logger.warning(f"This is in deactivate_actions: {e}")
            return {"error": "Somthing went wrong in deactivation"}




class LogsServices:
    def __init__(self, action: AccountService, user: UserAccount):
        self.action = action
        self.moniter = action.connection_id
        self.frequency = action.frequency_hour
        self.created_at = action.created_at
        self.user = user

    def _get_limit_logs(self, moniter: Moniter, action: AccountService):
        limits = get_workable_range(action=action)
        query_set = PingLogs.objects.filter(moniter=moniter)

        for limit in limits:
            lower_limit = limit[0]
            upper_limit = limit[1]
            
            if not upper_limit:
                query_set = query_set.filter(timestamp__gte=lower_limit)
            else:
                query_set = query_set.filter(timestamp__gte=lower_limit, timestamp__lte=upper_limit)
        
        return query_set
    
    def _get_frequency_logs(self, frequency: float, action: AccountService, query_set):
        target_count = int(frequency) 
        log_ids = list(query_set.order_by('timestamp').values_list('id', flat=True))
        total_logs = len(log_ids)

        if total_logs <= target_count or target_count <= 0:
            return query_set # Return everything if they want more than we have
        step = total_logs // target_count

        sampled_ids = log_ids[::step][:target_count]

        return query_set.filter(id__in=sampled_ids)

    
    def get_logs(self):
        if not self.user:
            return None
        
        user_checks = CheckUser(user=self.user, action=self.action)

        try:
            user_data = user_checks.get_info()
            logger.info(user_data)
            
            queryset_logs = self._get_limit_logs(action=self.action, moniter=self.moniter)
            logger.info(f"Queryset is working: {queryset_logs}")
            #queryset_logs = self._get_frequency_logs(query_set=queryset_logs, frequency=self.action.frequency_hour)

            logger.info("try for the get_logs works fine so far")
            return queryset_logs
        except Exception as e:
            logger.warning(f"Error is in get_logs services: {e}")


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

