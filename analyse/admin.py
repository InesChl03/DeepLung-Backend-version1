from django.contrib import admin
from .models import Analyse, Nodule


@admin.register(Analyse)
class AnalyseAdmin(admin.ModelAdmin):
    list_display  = ["get_patient", "statut", "nodule_count", "max_probability", "niveau_risque", "created_at"]
    list_filter   = ["statut", "niveau_risque"]
    ordering      = ["-created_at"]

    def get_patient(self, obj):
        p = obj.dossier.patient
        return f"{p.nom} {p.prenom}"
    get_patient.short_description = "Patient"


@admin.register(Nodule)
class NoduleAdmin(admin.ModelAdmin):
    list_display  = ["get_patient", "diameter_mm", "probability", "risk"]
    list_filter   = ["risk"]
    ordering      = ["-probability"]

    def get_patient(self, obj):
        p = obj.analyse.dossier.patient
        return f"{p.nom} {p.prenom}"
    get_patient.short_description = "Patient"