# settings.py

# Celery configuration
import os
from celery import Celery

from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'splitwise_app.settings')

app = Celery('splitwise_app')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'debit-reminder': {
        'task': 'expenses.tasks.weeekly_notification_task',
        'schedule': crontab(minute='0', hour='0', day_of_week='1'),
        'options': {'queue': settings.NOTIFICATION_QUEUE},
        'args': ()
    }
}
