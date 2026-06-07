from django.urls import path
from .views import PatientListCreateView, PatientDetailView

app_name = "patients"

urlpatterns = [
    path("",      PatientListCreateView.as_view(), name="patient-list-create"),
    path("<int:pk>/", PatientDetailView.as_view(),     name="patient-detail"),
]

# Dans ton root urls.py ajoute :
# path("api/patients/", include("patients.urls")),