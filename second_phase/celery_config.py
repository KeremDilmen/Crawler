from celery import Celery

app = Celery(
    'tasks',
    broker='pyamqp://guest@localhost//',
    backend='rpc://'
)

app.conf.task_routes = {
    'tasks.fetch_all_companies': {'queue': 'fetch'},
    'tasks.fetch_enterprise_details': {'queue': 'details'},
    'tasks.save_to_json': {'queue': 'save'},
    'tasks.run_analysis': {'queue': 'analysis'},
}

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Import the tasks module to ensure the tasks are registered
import tasks

