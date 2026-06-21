from celery import shared_task

from .models import Job
from .services import TransactionProcessor

@shared_task(bind=True, autoretry_for=(Exception,),retry_backoff=True,retry_kwargs={"max_retries":3})
def process_job(self, job_id):
    job = Job.objects.get(id=job_id)

    try:
        job.status = "processing"
        job.save()

        processor = TransactionProcessor()

        results = processor.process(job.file)

        job.results = results

        job.status = "finished"

    except Exception as e:
        job.status = "failed"
        job.error = str(e)

    finally:
        job.save()