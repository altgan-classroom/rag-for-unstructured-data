# celery_app.py
from celery import Celery
from .config import config

def make_celery():
    app = Celery(
        'document_queue',
        broker=config.REDIS_URL,
        backend=config.REDIS_URL
    )
    app.conf.update(
        result_expires=config.CELERY_RESULT_EXPIRES,
        task_track_started=config.CELERY_TASK_TRACK_STARTED,
        task_time_limit=config.CELERY_TASK_TIME_LIMIT,
        worker_prefetch_multiplier=config.CELERY_WORKER_PREFETCH_MULTIPLIER,
        worker_concurrency=config.CELERY_WORKER_CONCURRENCY
    )
    return app

celery_app = make_celery()

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'check-queue-health': {
        'task': 'core.ingest.tasks.check_queue_health',
        'schedule': 300.0,  # Run every 5 minutes
    },
}