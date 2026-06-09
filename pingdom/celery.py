import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pingdom.settings')

app = Celery('pingdom')
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'


app.conf.beat_schedule = {
    'run-monitors-every-minute': {
        'task': 'actions.tasks.run_moniters', # Change 'your_app_name' to your real Django app name
        'schedule': crontab(minute='*'), # runs every single minute
    },
}