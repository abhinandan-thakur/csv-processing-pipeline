from django.db import models

# Create your models here.
class Job(models.Model):
    file=models.FileField(upload_to='uploads/')
    status=models.CharField(max_length=40)
    filename=models.CharField(max_length=255)
    created_at=models.DateTimeField(auto_now_add=True)
    completed_at=models.DateTimeField(null=True, blank=True)
    error=models.CharField(null=True, blank=True)
    row_count_raw=models.IntegerField(default=0)
    row_count_clean=models.IntegerField(default=0)
    results=models.JSONField(null=True, blank=True)
