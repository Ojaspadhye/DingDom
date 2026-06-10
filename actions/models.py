from django.db import models

# Create your models here.

class Moniter(models.Model):
    #user = models.ForeignKey()
    urls = models.URLField()
    name = models.CharField(max_length=100)
    frequency_hour = models.CharField(default=5)
    expected_status = models.IntegerField(default=200)
    is_active = models.BooleanField(default=True)
    last_checked = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PingLogs(models.Model):
    moniter = models.ForeignKey(Moniter, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    response_time = models.FloatField(max_length=10)
    status_code = models.IntegerField(null=True)
    error_message = models.TextField(null=True, blank=True)
    is_sucess = models.BooleanField()
    avg_5hr = models.FloatField(null=True)
    avg_5req = models.FloatField(null=True)
    std_5hr = models.FloatField(null=True)
    std_5req = models.FloatField(null=True)

