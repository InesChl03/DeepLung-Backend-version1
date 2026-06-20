from rest_framework import serializers
from classification.models import NoduleClassification


class NoduleClassificationSerializer(serializers.ModelSerializer):
    label_str = serializers.SerializerMethodField()

    class Meta:
        model = NoduleClassification
        fields = [
            "id",
            "nodule_id_ticnet",
            "rang",
            "voxel_x", "voxel_y", "voxel_z",
            "diametre_mm",
            "prob_detection",
            "label",
            "label_str",
            "proba_maligne",
            "proba_benigne",
            "created_at",
        ]

    def get_label_str(self, obj):
        return "Maligne" if obj.label == 1 else "Benigne"