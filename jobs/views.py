from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Job
from .serializers import JobSerializer, JobListSerializer

from .tasks import process_job

import time

import logging

logger = logging.getLogger(__name__)

class JobView(APIView):
    def post(self, request):
        start = time.perf_counter()

        serializer = JobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validation_end = time.perf_counter()

        uploaded_file = serializer.validated_data["file"]

        job = Job.objects.create(
            file=uploaded_file,
            filename=uploaded_file.name,
            status="pending"
        )

        db_end = time.perf_counter()

        process_job.delay(job.id)

        celery_end = time.perf_counter()

        return Response(
            {
                "job_id": job.id,
                "status": "pending"
            },
            status=202
        )

class JobListView(APIView):
    def get(self, request):
        queryset = Job.objects.all()

        status_filter = request.query_params.get("status")

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        start = (page - 1) * page_size
        end = start + page_size

        total = queryset.count()

        jobs = queryset.values(
            "id",
            "status",
            "filename",
            "row_count_clean",
            "row_count_raw",
            "created_at"
        )[start:end]

        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": list(jobs)
        })

class JobStatusView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(Job, id=job_id )
        return Response({"id": job.id, "status": job.status},200)

class JobResultView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        return Response({"id": job.id, "result": job.results},200)