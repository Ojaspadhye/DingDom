from django.test import TestCase
from rest_framework.test import (APITestCase, APIClient)
from actions.models import (Moniter, PingLogs)
from django_celery_beat.models import (
    PeriodicTask, PeriodicTasks,
)
from actions.services import (MoniterLogServices, LogKpisServices, LogsServices)
from rest_framework import status
import json
# Create your tests here.

class TestActions(APITestCase):
    action_1 = {
        "urls": "https://www.youtube.com/watch?v=vynvegQ9Ecw&t=858s",
        "name": "up",
        "frequency": 45,
        "expected_status": 200,
        "is_active": True
    }

    data = {
        "urls": "https://www.tomscatwebsite.com/",
        "name": "Toms Cat",
        "frequency": 45,
        "expected_status": 200,
        "is_active": True
    }
    
    def setUp(self):
        self.client = APIClient()

        self.client.post(path="/action/action/create_action/",
            data=self.data,
            format="json"
        )

    def test_create_action(self):
        moniter_count = Moniter.objects.count()
        tasks_count = PeriodicTasks.objects.count()

        response = self.client.post(path="/action/action/create_action/", data=self.action_1, format="json")
        response_data = response.data
        id = (response_data.get("action").get("id"))

        moniter = Moniter.objects.filter(id=id).first()
        task = PeriodicTask.objects.latest("args")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(moniter_count + 1, Moniter.objects.count())
        self.assertTrue(Moniter.objects.filter(id=id).exists())
        self.assertEqual(PeriodicTask.objects.count(), tasks_count + 1)

        self.assertEqual(moniter.name, self.action_1["name"])
        self.assertEqual(moniter.urls, self.action_1["urls"])
        self.assertTrue(moniter.is_active)

        self.assertIn(str(id), str(task.args))

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
    response_time = models.FloatField(max_length=10)
    status_code = models.IntegerField(null=True)
    error_message = models.TextField(null=True, blank=True)
    is_sucess = models.BooleanField()
    avg_5hr = models.FloatField(null=True)
    avg_5req = models.FloatField(null=True)
    std_5hr = models.FloatField(null=True)
    std_5req = models.FloatField(null=True)
'''
class LogsTest():
    response_1 = {
        "response_time": 1.587523846,
        "status_code": status.HTTP_200_OK,
        "error_message": None,
    }

    response_1 = {
        "response_time": 2.846365982,
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "error_message": "Cool! I am optimestic. I couldent think of any error message",
    }

    hr5_kpi = {
        "average": 1.846365982
    }

    def setUp(self):
        self.moniter = Moniter.objects.create(
            urls="https://httpbin.org/status/200",
            name="httpbin",
            frequency_hour=45,
            expected_status=200,
            is_active=True
        )

    def test_log_created(self):
        self.moniter


    def get_update(self):
        pass

    def kpis_1(self):
        pass

    def kpis_2(self):
        pass