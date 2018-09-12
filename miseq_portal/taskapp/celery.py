from __future__ import absolute_import

import os
from django.apps import apps, AppConfig
from django.conf import settings
from celery import Celery

from raven import Client as RavenClient
from raven.contrib.celery import register_signal as raven_register_signal
from raven.contrib.celery import register_logger_signal as raven_register_logger_signal

"""
http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html#using-celery-with-django
Other Celery config is in config.settings.base
"""

import logging

logger = logging.getLogger('raven')

if not settings.configured:
    # set the default Django settings module for the 'celery' program.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')  # pragma: no cover

app = Celery('miseq_portal')


class CeleryAppConfig(AppConfig):
    name = 'miseq_portal.taskapp'
    verbose_name = 'Celery Config'

    def ready(self):
        # Using a string here means the worker will not have to
        # pickle the object when using Windows.
        # - namespace='CELERY' means all celery-related configuration keys
        #   should have a `CELERY_` prefix.
        app.config_from_object('django.conf:settings', namespace='CELERY')
        app.autodiscover_tasks()

        raven_client = RavenClient(dsn=settings.RAVEN_CONFIG['dsn'])
        raven_register_logger_signal(raven_client)
        raven_register_signal(raven_client)

        logger.info(f"Celery backend: {app.backend}")
        logger.info(f"Celery broker_connection: {app.broker_connection()}")
        logger.info(f"Raven client: {raven_client}")
        # logger.info(f"Apps: {apps}")
        # logger.info(apps.get_app_configs())
        # for key, val in app.tasks.items():
        #     logger.info(key)


@app.task(bind=True)
def debug_task(self):
    logger.info(f'Request: {self.request!r}')  # pragma: no cover
