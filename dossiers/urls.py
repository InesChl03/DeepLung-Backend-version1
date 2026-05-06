from django.urls import path
from .views import (
    DossierDetailView,
    FichierUploadView,
    FichierDeleteView,
    RapportUpdateView,
)

app_name = "dossiers"

urlpatterns = [
    path("<int:patient_id>/",                              DossierDetailView.as_view(),  name="dossier-detail"),
    path("<int:patient_id>/fichiers/",                     FichierUploadView.as_view(),  name="fichier-upload"),
    path("<int:patient_id>/fichiers/<int:fichier_id>/",    FichierDeleteView.as_view(),  name="fichier-delete"),
    path("<int:patient_id>/rapport/",                      RapportUpdateView.as_view(),  name="rapport-update"),
]

# Dans root urls.py :
# path("api/dossiers/", include("dossiers.urls")),