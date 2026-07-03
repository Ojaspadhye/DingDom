from django.test import TestCase
from rest_framework.test import (APITestCase, APIClient)
from actions.models import (Moniter, PingLogs, PingLogsKpis)
from django_celery_beat.models import (
    PeriodicTask, PeriodicTasks,
)
from accounts.models import (UserAccount, AccountTier)
from actions.services import (MoniterLogServices, LogKpisServices, LogsServices, AccountService)
from rest_framework import status
import json
from unittest.mock import patch, MagicMock
from .models import Moniter, PingLogs
from .services import MoniterLogServices
from django.utils import timezone
from datetime import timedelta
from freezegun import freeze_time
# Create your tests here.

class TestActions(APITestCase):
    action_1 = {
        "urls": "https://httpbin.org/status/200",
        "name": "http_bin",
        "frequency": 12,
        "expected_status": 200,
        "is_active": True
    }

    data = {
        "urls": "https://httpbin.org/status/200",
        "name": "http_bin",
        "frequency": 5,
        "expected_status": 200,
        "is_active": True 
    }

    data_1 = {
        "urls": "https://theuselessweb.com/",
        "name": "cool",
        "frequency": 2,
        "expected_status": 200,
        "is_active": True
    }
        
    def setUp(self):
            user = UserAccount.objects.create(
                username="Ojas_Padhye",
                email="ojaspadhye@gmail.com",
                is_active=True,
                is_staff=False,
            )
            user.set_password("IDontKnow123")
            user.save()

            AccountTier.objects.create(
                account=user,
                limit=5
            )
            
            self.client = APIClient()

            response = self.client.post(
                path="/accounts/accounts/login_account/",
                data={
                    "username": "Ojas_Padhye",
                    "password": "IDontKnow123"
                },
                format="json"
            )


            access_token = response.data.get("tokens").get("access token")
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')


    def test_create_action(self):
        moniter_count = Moniter.objects.count() # As this is the first thing being created moniter should increase
        action_count = AccountService.objects.count()
        tasks_count = PeriodicTasks.objects.count()

        response = self.client.post(path="/action/action/create_action/", data=self.action_1, format="json")
        response_data = response.data
        
        id = (response_data.get("action").get("id"))

        action = AccountService.objects.filter(id=id).first()
        moniter = Moniter.objects.filter(id=id).first()

        self.assertEqual(action.connection_id, moniter)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(moniter_count + 1, Moniter.objects.count())
        self.assertTrue(Moniter.objects.filter(id=id).exists())
        self.assertEqual(PeriodicTask.objects.count(), tasks_count + 1)

        self.assertEqual(moniter.urls, self.action_1["urls"])
        self.assertTrue(moniter.is_active)
    

    def test_create_multiple_action(self):
        moniter_count = Moniter.objects.count()
        actions = AccountService.objects.count()
        
        response_1 = self.client.post(path="/action/action/create_action/", data=self.action_1, format="json")
        id_1 = response_1.data.get("action").get("id")

        response_2 = self.client.post(path="/action/action/create_action/", data=self.data, format="json")
        id_2 = response_2.data.get("action").get("id")

        action_1 = AccountService.objects.get(id=id_1).connection_id
        action_2 = AccountService.objects.get(id=id_2).connection_id

        moniter_1_url = action_1.urls
        moniter_2_url = action_2.urls

        self.assertEqual(moniter_count + 1, Moniter.objects.count())
        self.assertEqual(actions + 2, AccountService.objects.count())

        self.assertIsNotNone(action_1)
        self.assertIsNotNone(action_2)

        self.assertEqual(action_1, action_2)
        self.assertEqual(moniter_1_url, self.action_1.get("urls"))
        self.assertEqual(moniter_2_url, self.data.get("urls"))


    def test_create_different_action(self):
        moniter_count = Moniter.objects.count()
        actions_count = AccountService.objects.count()

        response_1 = self.client.post(path="/action/action/create_action/", data=self.action_1, format="json")
        response_2 = self.client.post(path="/action/action/create_action/", data=self.data_1, format="json")

        id_1 = response_1.data.get("action").get("id")
        id_2 = response_2.data.get("action").get("id")

        action_1 = AccountService.objects.get(id=id_1)
        action_2 = AccountService.objects.get(id=id_2)

        moniter_1 = action_1.connection_id
        moniter_2 = action_2.connection_id

        self.assertEqual(moniter_count + 2, Moniter.objects.count())
        self.assertEqual(actions_count + 2, AccountService.objects.count())

        self.assertIsNotNone(moniter_1)
        self.assertIsNotNone(moniter_2)

        self.assertNotEqual(moniter_1, moniter_2)
        self.assertNotEqual(moniter_1.urls, moniter_2.urls)
        self.assertEqual(moniter_1.urls, self.action_1.get("urls"))
        self.assertEqual(moniter_2.urls, self.data_1.get("urls"))



    '''

    def test_update_action_1(self):
        action_1_update = {
            "name": "Kitten",
            "frequency": 20,
            "expected_status": 404,
        }

        response = self.client.patch(path="/action/action/1/update_actions/", data=action_1_update, format="json")

        response_data = response.data.get("action")
        new_name = response_data.get("name")
        new_status_code = response_data.get("conditions").get("expected_status")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(new_name, action_1_update.get("name"))
        self.assertNotEqual(new_name, self.data.get("name"))
        self.assertEqual(new_status_code, action_1_update.get("expected_status"))
        self.assertNotEqual(new_status_code, self.data.get("expected_status"))

    def test_deactivate_action(self):
        pass

    def test_hard_delete_action(self):
        pass
    '''


'''
    response_time = models.FloatField(max_length=10)
    status_code = models.IntegerField(null=True)
    error_message = models.TextField(null=True, blank=True)
    is_sucess = models.BooleanField()
    avg_5hr = models.FloatField(null=True)
    avg_5req = models.FloatField(null=True)
    std_5hr = models.FloatField(null=True)
    std_5req = models.FloatField(null=True)
'''


class LogsTest(APITestCase):
    action_1 = {
        "urls": "https://httpbin.org/status/200",
        "name": "http_bin",
        "frequency": 12,
        "expected_status": 200,
        "is_active": True
    }

    action_2 = {
        "urls": "https://httpbin.org/status/200",
        "name": "http_bin",
        "frequency": 5,
        "expected_status": 200,
        "is_active": True 
    }

    response_1 = {
        "response_time": 1.587523846,
        "status_code": status.HTTP_200_OK,
        "error_message": None,
    }

    response_2 = {
        "response_time": 2.846365982,
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "error_message": "Cool! I am optimestic. I couldent think of any error message",
    }

    hr5_kpi = {
        "average": 1.846365982
    }

    def setUp(self):
        self.moniter_magic = MagicMock()

        self.user = UserAccount.objects.create(
            username="Ojas_Padhye",
            email="ojaspadhye@gmail.com",
            is_active=True,
            is_staff=False,
        )
        self.user.set_password("IDontKnow123")
        self.user.save()

        AccountTier.objects.create(
            account=self.user,
            limit=5
        )

        self.client = APIClient()

        # Login doesn't usually need a frozen time context unless token expiry is tight
        response = self.client.post(
            path="/accounts/accounts/login_account/",
            data={
                "username": "Ojas_Padhye",
                "password": "IDontKnow123"
            },
            format="json"
        )
        access_token = response.data.get("tokens").get("access token")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')


    def test_log_created_and_monitored_chronologically(self):
        """Test that user actions and monitoring happen in strict chronological order."""
        
        # 1. Start the timeline freeze at 12:00:00
        with freeze_time("2026-07-03 12:00:00") as frozen_time:
            
            # 2. Trigger Action 1
            response_1 = self.client.post(
                path="/action/action/create_action/",
                data=self.action_1,
                format="json"
            )
            
            # Grab the service state right after Action 1
            action_R1 = AccountService.objects.get(id=response_1.data.get("id"))
            monitor_1 = action_R1.connection_id
            
            # Assert things look right for 12:00:00 here...
            
            # -------------------------------------------------------------
            # 3. Move time forward 3 hours (12:00:00 -> 15:00:00)
            # -------------------------------------------------------------
            frozen_time.move_to("2026-07-03 15:00:00")
            
            # 4. Trigger Action 2 (Now executes perfectly at 15:00:00)
            response_2 = self.client.post(
                path="/action/action/create_action/",
                data=self.action_2,
                format="json"
            )
            
            action_R2 = AccountService.objects.get(id=response_2.data.get("id"))
            monitor_2 = action_R2.connection_id

            # 5. Perform your simultaneous assertions
            # Check your monitoring mock or verification logs here
            # e.g., self.assertEqual(monitor_2.some_timestamp, timezone.now())

    @patch("requests.get")
    def test_successful_ping_creates_log(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        service = MoniterLogServices(moniter=self.moniter)

        result = service.create_logs()

        self.assertIsNotNone(result["log"])
        self.assertEqual(result["status_code"], 200)
        self.assertTrue(result["is_sucess"])

        self.assertEqual(PingLogs.objects.count(), 1)
        
    '''
    @patch("requests.get")
    def test_503_ping_records_failure(self, mock_get, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.json.return_value = {"message": "system error"} 

        mock_get.return_value = mock_response

        service = MoniterLogServices(self.moniter)
        result = service.create_logs()

        self.assertIsNotNone(result["log"])
        self.assertEqual(result["status_code"], 503)
        self.assertFalse(result["is_sucess"])

        self.assertEqual(PingLogs.objects.count(), 1)

    @freeze_time("2026-06-17 12:00:00")
    @patch("requests.get")
    def test_5hr_averages(self, *args, **kwargs):
        now = timezone.now()

        PingLogs.objects.create(
            moniter=self.moniter,
            timestamp=now - timedelta(hours=1),
            response_time=2.747583,
            status_code=200,
            error_message=None,
            is_sucess=True,
        )

        PingLogs.objects.create(
            moniter=self.moniter,
            timestamp=now - timedelta(hours=2),
            response_time=1.523712,
            status_code=200,
            error_message=None,
            is_sucess=True,
        )

        PingLogs.objects.create(
            moniter=self.moniter,
            timestamp=now - timedelta(hours=5),
            response_time=2.132424,
            status_code=200,
            error_message=None,
            is_sucess=True,
        )

        PingLogs.objects.create(
            moniter=self.moniter,
            timestamp=now - timedelta(hours=6),
            response_time=6.2645932,
            status_code=200,
            error_message=None,
            is_sucess=True,
        )

        before_count = PingLogsKpis.objects.count()

        calculated_average = float((2.747583 + 2.132424 + 1.523712)/3)

        kpi_5hr = LogKpisServices(condition=1 ,moniter=self.moniter).create_ping_kpis()

        self.assertEqual((before_count + 1), PingLogsKpis.objects.count())
        self.assertAlmostEqual(calculated_average, kpi_5hr.average, places=5)
        
        delta = abs(((now + timedelta(hours=5)) - kpi_5hr.cal_timestamp).total_seconds())
        self.assertLessEqual(60, delta)

    @freeze_time("2026-06-17 12:00:00")
    @patch("requests.get")
    def test_5hr_average_unhappy_path(self, *args, **kwargs):
        now = timezone.now()

        PingLogs.objects.create(
            moniter=self.moniter,
            timestamp=now - timedelta(hours=4),
            response_time=None,
            status_code=200,
            error_message=None,
            is_sucess=True,
        )

        expected_average = 0

        before_count = PingLogsKpis.objects.count()

        kpi_5hr = LogKpisServices(condition=1 ,moniter=self.moniter).create_ping_kpis()

        self.assertEqual((before_count + 1), PingLogsKpis.objects.count())
        self.assertEqual(expected_average, kpi_5hr.average)

    
    @freeze_time("2026-06-17 12:00:00")
    @patch("requests.get")
    def test_average_5hr_update(self, mock_get, *args, **kwargs):
        kpi_log = PingLogsKpis.objects.create(
            moniter=self.moniter,
            cal_timestamp=timezone.now(),
            average=2.347535,
            cal_timestamp_end=timezone.now() + timedelta(hours=5)
        )

        self.moniter_magic.status_code = 200
        mock_get.return_value = self.moniter_magic

        service = MoniterLogServices(self.moniter)

        result = service.create_logs(kpi=kpi_log)
        print(result)

        self.assertIsNotNone(result["log"])
        self.assertEqual(result["status_code"], 200)
        self.assertTrue(result["is_sucess"])

        self.assertEqual(PingLogs.objects.count(), 1)
        self.assertIsNotNone(result["log"])

        created_log = result.get("log")

        self.assertIsNotNone(created_log.avg_5hr)
        self.assertEqual(created_log.avg_5hr, kpi_log.average)
    '''

