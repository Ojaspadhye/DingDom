from django.db import transaction
from actions.models import (Moniter, PingLogs, PingLogsKpis, AccountService)
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from actions.models import (AccountService)
from django_celery_beat.models import (PeriodicTask, PeriodicTasks, IntervalSchedule)
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

class TimeWheelSchedule:
    def __init__(self, schedule: IntervalSchedule, periodic_task: PeriodicTasks):
        self.schedule = schedule
        self.periodic_task = periodic_task
        self.wheel_size = 12
        self.tick_duration_mins = 5
        self.counter = 0
        self.slot = [deque() for _ in range(self.wheel_size)]

    def adition_task(self, action: AccountService):
        interval_mins = int(float(action.frequency_hour) * 60)

        if interval_mins % self.tick_duration_mins != 0:
            interval_mins = max(
                self.tick_duration_mins,
                (interval_mins // self.tick_duration_mins) * self.tick_duration_mins
            )
        
        total_ticks_needed = interval_mins // self.tick_duration_mins
        target_slot = (self.counter + total_ticks_needed) % self.wheel_size

        laps = total_ticks_needed // self.wheel_size

        payload = {
            "action_id": action.id,
            "moniter_id": action.connection_id.id if action.connection_id else None,
            "url": action.url,
            "expected_status": action.expected_status,
            "remaning_laps": laps,
            "interval_mins": interval_mins
        }

        self.slots[target_slot].append(payload)


    def tick(self, ):
        self.counter = (self.counter + 1) % self.wheel_size
        bucket = self.slot[self.counter]

        tasks_run = []
        waiting_task = deque()

        while bucket:
            task = bucket.popleft()

            if task["remaning_laps"] > 0:
                task["remaning_laps"] -= 1
                waiting_task.append(task)
            
            else:
                tasks_run.append(task)
        
        self.slot[self.counter] = waiting_task

        moniter_groups = {}
        for task in tasks_run:
            moniter_id = task["moniter_id"]
            if moniter_id not in moniter_groups:
                moniter_groups[moniter_id] = []
            
            moniter_groups[moniter_id].append(task)

        for moniter_id, grouped_taks in moniter_groups.items():
            representative_task = grouped_taks[0]
            url = representative_task["url"]

            try:
                ## Loging Thingi
                pass
            except:
                ## Few other things 
                pass


class ActionServices:
    def __init__(self, data=None, user=None):
        self.user = user
        self.data = data

    def _check_multiple(self, freq_1, freq_2):
        response = False
        common_multiple = None

        if (freq_1 % freq_2 == 0):
            response=True
            common_multiple = freq_2

        elif (freq_2 % freq_1 == 0):
            response = True
            common_multiple = freq_1

        return response, common_multiple
    


    def _check_and_create_action(self, action: AccountService):
        if not action:
            raise Exception()
        
        urls = action.urls

        try:
            with transaction.atomic():
                moniter, created = Moniter.objects.get_or_create(
                    urls=urls,
                    frequency_hour=action.frequency_hour,
                    is_active=True
                )

                if created:
                    schedule, _ = IntervalSchedule.objects.get_or_create(
                        id=moniter.id,
                        defaults =  {
                            'every' :action.frequency_hour,
                            'period' : IntervalSchedule.HOURS
                        }
                    )

                    PeriodicTask.objects.create(
                        interval=schedule,
                        name=f'Ping Monitor {action.id}',
                        task='actions.tasks.universal_ping_worker',
                        args=json.dumps([action.id]),
                    )
                
                else:
                    schedule = IntervalSchedule.objects.filter(id=moniter.id).first()
                    periodic_task = PeriodicTask.objects.filter(interval=schedule).first()

                    time_scheduler = TimeWheelSchedule(schedule=schedule, periodic_task=periodic_task)
                    scheduled_response = time_scheduler.schedule()

                    if "error" in scheduled_response:
                        return {
                            "error": "Somthing went wrong in scheduling"
                        }
                    




                existing_frequency = moniter.frequency_hour
                demanded_frequency = action.frequency_hour

                    

                action.connection_id = moniter
                action.save(update_fields=["connection_id"])

        except:
            return

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
                    urls=urls,
                    name=name,
                    frequency_hour=freq,
                    expected_status=status,
                    is_active=is_active
                )


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

