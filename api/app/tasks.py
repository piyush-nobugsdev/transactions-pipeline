import time

from app.celery_app import celery_app


@celery_app.task(name="app.tasks.ping")
def ping() -> str:
    """Dummy task: sleeps 1s then returns 'pong'.

    Stand-in for the real pipeline task we'll write once the
    upload endpoint + data model exist. Proves: API -> Redis ->
    worker -> Redis (result backend) -> API works end to end.
    """
    time.sleep(1)
    return "pong"
