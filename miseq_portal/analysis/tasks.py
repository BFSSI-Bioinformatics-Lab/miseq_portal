from __future__ import absolute_import, unicode_literals
from celery import shared_task
from miseq_portal.taskapp.celery import app


# @shared_task()

# @app.task()
@shared_task()
def add(x, y):
    return x + y
