# AI_transaction_processing_pipeline/celery.py

import os

from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "AI_transaction_processing_pipeline.settings"
)

app = Celery("AI_transaction_processing_pipeline")

app.config_from_object(
    "django.conf:settings",
    namespace="CELERY"
)

app.autodiscover_tasks()