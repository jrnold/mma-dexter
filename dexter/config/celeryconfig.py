from celery.schedules import crontab
from datetime import timedelta

BROKER_URL = 'amqp://guest:guest@localhost:5672'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT=['json']
CELERY_TIMEZONE = 'Africa/Johannesburg'
CELERY_ENABLE_UTC = True

CELERYBEAT_SCHEDULE = {
    'fetch-yesterdays-feeds': {
        'schedule': crontab(hour=2, minute=0),
        'task': 'dexter.tasks.fetch_yesterdays_feeds',
    },
}
