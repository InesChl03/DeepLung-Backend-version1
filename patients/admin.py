from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display  = ["nom", "prenom", "age", "sexe", "telephone", "get_doctor"]
    list_filter   = ["sexe"]
    search_fields = ["nom", "prenom", "telephone"]
    ordering      = ["-created_at"]

    def get_doctor(self, obj):
        return obj.doctor.full_name
    get_doctor.short_description = "Médecin"