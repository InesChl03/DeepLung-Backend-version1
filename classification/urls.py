from django.urls import path
from classification import views

urlpatterns = [
    # Récupère (ou déclenche) la classification d'un scan
    path("scan/<int:scan_id>/",          views.get_classification,      name="classification-get"),
    # Force une re-classification
    path("scan/<int:scan_id>/relancer/", views.relancer_classification,  name="classification-relancer"),
]