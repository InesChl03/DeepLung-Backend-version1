from django.urls import path
from .views import LancerAnalyseView, AnalyseDetailView, SlicesListView

app_name = "analyse"

urlpatterns = [
    # Lance une analyse sur un fichier médical
    path(
        "<int:patient_id>/fichiers/<int:fichier_id>/lancer/",
        LancerAnalyseView.as_view(),
        name="lancer-analyse"
    ),

    # Liste toutes les analyses d'un patient
    path(
        "<int:patient_id>/resultats/",
        AnalyseDetailView.as_view(),
        name="analyse-list"
    ),

    # Détail d'une analyse spécifique
    path(
        "<int:patient_id>/resultats/<int:analyse_id>/",
        AnalyseDetailView.as_view(),
        name="analyse-detail"
    ),

    # Slices PNG d'une analyse
    path(
        "<int:patient_id>/resultats/<int:analyse_id>/slices/",
        SlicesListView.as_view(),
        name="analyse-slices"
    ),
]

# Dans root urls.py ajoute :
# path("api/analyse/", include("analyse.urls")),