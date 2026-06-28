"""
Celery application instance for the AnimeClip project.

Start workers:
    celery -A Hello worker -l info

Start the periodic scheduler (beat):
    celery -A Hello beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

Or run both together in development:
    celery -A Hello worker --beat -l info
"""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hello.settings')

app = Celery('Hello')

# Read config from Django settings under the CELERY_ namespace.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py modules in every INSTALLED_APP.
app.autodiscover_tasks()
