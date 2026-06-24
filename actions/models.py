from django.db import models

# Create your models here.

class AccountService(models.Model):
    account = models.ForeignKey("accounts.UserAccount", on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=True)
    url = models.URLField()
    frequency_hour = models.CharField(default=5)
    expected_status = models.IntegerField(default=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Moniter(models.Model):
    urls = models.URLField()
    frequency_hour = models.CharField(default=5)
    is_active = models.BooleanField(default=True)
    last_checked = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    #deleted = models.BooleanField(default=False)
    #name = models.CharField(max_length=100)
    #expected_status = models.IntegerField(default=200) # I dont think i will need them anymore
    #user = models.ForeignKey()
    
# I Have made a big mistake of doing devication insted of standard deviation. I will clean in cleaning rounds
class PingLogs(models.Model):
    moniter = models.ForeignKey(Moniter, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    response_time = models.FloatField(max_length=10, default=0, null=True)
    status_code = models.IntegerField(null=True)
    error_message = models.TextField(null=True, blank=True)
    is_sucess = models.BooleanField()
    avg_5hr = models.FloatField(null=True)
    avg_5req = models.FloatField(null=True)
    std_5hr = models.FloatField(null=True)
    std_5req = models.FloatField(null=True)


class PingLogsKpis(models.Model):
    moniter = models.ForeignKey(Moniter, on_delete=models.CASCADE)
    cal_timestamp = models.DateTimeField() # When 5hr average was calculated
    average = models.FloatField(default=0.0)
    cal_timestamp_end = models.DateTimeField() # Expected Expiry time for this log. This is for refrence and testing only

