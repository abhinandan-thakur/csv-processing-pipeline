from django.urls import path, include
from .views import JobView, JobListView, JobStatusView, JobResultView
from django.conf import settings

urlpatterns=[
    path('upload/', JobView.as_view(), name='job-upload'),
    path('', JobListView.as_view(), name='job-list-upload'),
    path('<int:job_id>/status/',JobStatusView.as_view(), name='job-status-upload'),
    path('<int:job_id>/result/', JobResultView.as_view(), name='job-result-upload'),
]

if settings.PROFILING:
    urlpatterns += [
        path("silk/", include("silk.urls", namespace="silk")),
    ]