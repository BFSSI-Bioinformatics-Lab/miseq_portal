from __future__ import absolute_import

from django.apps import apps, AppConfig
from celery import Celery

"""
http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html#using-celery-with-django
Other Celery config is in config.settings.base
"""

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
        installed_apps = [app_config.name for app_config in apps.get_app_configs()]
        app.autodiscover_tasks(lambda: installed_apps, force=True)


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')  # pragma: no cover
