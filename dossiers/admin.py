from django.contrib import admin
from .models import Dossier, FichierMedical, Rapport


@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    list_display  = ["get_patient", "created_at"]
    search_fields = ["patient__nom", "patient__prenom"]

    def get_patient(self, obj):
        return f"{obj.patient.nom} {obj.patient.prenom}"
    get_patient.short_description = "Patient"


@admin.register(FichierMedical)
class FichierMedicalAdmin(admin.ModelAdmin):
    list_display  = ["get_patient", "type_fichier", "uploaded_at"]
    list_filter   = ["type_fichier"]

    def get_patient(self, obj):
        return f"{obj.dossier.patient.nom} {obj.dossier.patient.prenom}"
    get_patient.short_description = "Patient"


@admin.register(Rapport)
class RapportAdmin(admin.ModelAdmin):
    list_display  = ["get_patient", "statut", "created_at"]
    list_filter   = ["statut"]

    def get_patient(self, obj):
        return f"{obj.dossier.patient.nom} {obj.dossier.patient.prenom}"
    get_patient.short_description = "Patient"