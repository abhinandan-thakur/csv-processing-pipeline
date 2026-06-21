from rest_framework import serializers
from .models import Job

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model=Job
        fields=["file"]

class JobListSerializer(serializers.ModelSerializer):
    class Meta:
        model=Job
        fields=['id','status','filename','created_at','row_count_clean','row_count_raw','error']