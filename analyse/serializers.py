from rest_framework import serializers
from .models import Analyse, Nodule


class NoduleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Nodule
        fields = [
            "id",
            "coordX", "coordY", "coordZ",
            "diameter_mm",
            "probability",
            "risk",
        ]


class AnalyseSerializer(serializers.ModelSerializer):
    nodules     = NoduleSerializer(many=True, read_only=True)
    patient_nom = serializers.SerializerMethodField()
    fichier_url = serializers.SerializerMethodField()

    class Meta:
        model  = Analyse
        fields = [
            "id",
            "patient_nom",
            "fichier_url",
            "statut",
            "nodule_count",
            "max_probability",
            "niveau_risque",
            "nodules",
            "erreur",
            "created_at",
            "updated_at",
        ]

    def get_patient_nom(self, obj):
        p = obj.dossier.patient
        return f"{p.nom} {p.prenom}"

    def get_fichier_url(self, obj):
        request = self.context.get("request")
        if obj.fichier_medical and obj.fichier_medical.fichier:
            url = obj.fichier_medical.fichier.url
            return request.build_absolute_uri(url) if request else url
        return None


class AnalyseListSerializer(serializers.ModelSerializer):
    patient_nom = serializers.SerializerMethodField()

    class Meta:
        model  = Analyse
        fields = [
            "id", "patient_nom",
            "statut", "nodule_count",
            "max_probability", "niveau_risque",
            "created_at",
        ]

    def get_patient_nom(self, obj):
        p = obj.dossier.patient
        return f"{p.nom} {p.prenom}"