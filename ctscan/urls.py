from django.urls import path
from .views import (
    CtScanAnalyserView,
    CtScanListView,
    CtScanDetailView,
    CtScanParDossierView,
)

urlpatterns = [
    # Lancer une analyse (upload .mhd + .raw)
    path('analyser/',                  CtScanAnalyserView.as_view(),    name='ctscan-analyser'),

    # Liste de tous les scans du médecin
    path('',                           CtScanListView.as_view(),        name='ctscan-list'),

    # Détail / suppression d'un scan
    path('<int:pk>/',                  CtScanDetailView.as_view(),      name='ctscan-detail'),

    # Tous les scans d'un dossier
    path('dossier/<int:dossier_id>/',  CtScanParDossierView.as_view(),  name='ctscan-par-dossier'),
]