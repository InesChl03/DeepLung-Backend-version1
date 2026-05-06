from rest_framework import serializers
from .models import Patient


class PatientListSerializer(serializers.ModelSerializer):
    """Utilisé dans la liste — champs essentiels uniquement."""

    class Meta:
        model  = Patient
        fields = [
            "id",
            "nom",
            "prenom",
            "age",
            "sexe",
            "telephone",
            "created_at",
        ]


class PatientDetailSerializer(serializers.ModelSerializer):
    """Utilisé dans le détail — tous les champs."""
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)

    class Meta:
        model  = Patient
        fields = [
            "id",
            "doctor_name",
            "nom",
            "prenom",
            "age",
            "sexe",
            "telephone",
            "adresse",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PatientCreateSerializer(serializers.ModelSerializer):
    """Utilisé pour créer un patient — le doctor est injecté depuis la vue."""

    class Meta:
        model  = Patient
        fields = [
            "nom",
            "prenom",
            "age",
            "sexe",
            "telephone",
            "adresse",
        ]

    def validate_age(self, value):
        if value <= 0 or value > 120:
            raise serializers.ValidationError("L'âge doit être entre 1 et 120.")
        return value

    def validate_telephone(self, value):
        if not value.replace("+", "").replace(" ", "").isdigit():
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        return value