from rest_framework import serializers
from .models import Dossier, FichierMedical, Rapport


class FichierMedicalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FichierMedical
        fields = ["id", "type_fichier", "fichier", "description", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class RapportSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Rapport
        fields = [
            "id", "statut", "resultat_ia",
            "notes_medecin", "conclusion",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "resultat_ia"]


class DossierSerializer(serializers.ModelSerializer):
    fichiers = FichierMedicalSerializer(many=True, read_only=True)
    rapport  = RapportSerializer(read_only=True)
    patient_nom = serializers.SerializerMethodField()

    class Meta:
        model  = Dossier
        fields = [
            "id", "patient_nom",
            "fichiers", "rapport",
            "created_at", "updated_at",
        ]

    def get_patient_nom(self, obj):
        return f"{obj.patient.nom} {obj.patient.prenom}"