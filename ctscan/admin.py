from django.contrib import admin
from django.contrib import admin
from .models import CtScan, Nodule


class NoduleInline(admin.TabularInline):
    model  = Nodule
    extra  = 0
    fields = ['rang', 'probabilite', 'diametre_mm', 'monde_z', 'monde_y', 'monde_x']
    readonly_fields = fields


@admin.register(CtScan)
class CtScanAdmin(admin.ModelAdmin):
    list_display  = ['id', 'get_patient', 'statut', 'get_nb_nodules', 'duree_analyse', 'created_at']
    list_filter   = ['statut']
    search_fields = ['dossier__patient__nom', 'dossier__patient__prenom']
    readonly_fields = ['created_at', 'updated_at', 'duree_analyse', 'message_erreur']
    inlines = [NoduleInline]

    def get_patient(self, obj):
        p = obj.dossier.patient
        return f"{p.nom} {p.prenom}"
    get_patient.short_description = "Patient"

    def get_nb_nodules(self, obj):
        return obj.nodules.count()
    get_nb_nodules.short_description = "Nodules"


@admin.register(Nodule)
class NoduleAdmin(admin.ModelAdmin):
    list_display  = ['id', 'rang', 'ctscan', 'probabilite', 'diametre_mm']
    list_filter   = ['ctscan__statut']
    search_fields = ['ctscan__dossier__patient__nom']