# src/real_time_auction/utils/celery_app.py
import os
from celery import Celery

def make_celery(app_name="real_time_auction"):
    celery = Celery(
        app_name,
        broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    )
    return celery

celery_app = make_celery()
