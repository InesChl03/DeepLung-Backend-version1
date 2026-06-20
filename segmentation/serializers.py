from rest_framework import serializers
from .models import NoduleSegmentation


class NoduleSegmentationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NoduleSegmentation
        fields = '__all__'