from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from accounts.permissions import IsDoctor
from patients.models import Patient
from .models import Dossier, FichierMedical, Rapport
from .serializers import DossierSerializer, FichierMedicalSerializer, RapportSerializer


def get_doctor(request):
    return request.user.doctor_profile


class DossierDetailView(APIView):
    """
    GET /api/dossiers/{patient_id}/
    Retourne le dossier complet du patient (fichiers + rapport).
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id, doctor=get_doctor(request))
        dossier = get_object_or_404(Dossier, patient=patient)
        return Response(DossierSerializer(dossier).data, status=status.HTTP_200_OK)


import zipfile
import tempfile
from django.core.files.storage import default_storage

class FichierUploadView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def post(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id, doctor=get_doctor(request))
        dossier = get_object_or_404(Dossier, patient=patient)

        type_fichier = request.data.get('type_fichier')
        fichier      = request.FILES.get('fichier')
        description  = request.data.get('description', '')

        if not fichier:
            return Response(
                {"error": "Fichier requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        medical_file = FichierMedical.objects.create(
            dossier      = dossier,
            type_fichier = type_fichier,
            fichier      = fichier,
            description  = description,
        )

        return Response(
            FichierMedicalSerializer(medical_file).data,
            status=status.HTTP_201_CREATED,
        )

class FichierDeleteView(APIView):
    """
    DELETE /api/dossiers/{patient_id}/fichiers/{fichier_id}/
    Supprime un fichier du dossier.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def delete(self, request, patient_id, fichier_id):
        patient = get_object_or_404(Patient, pk=patient_id, doctor=get_doctor(request))
        dossier = get_object_or_404(Dossier, patient=patient)
        fichier = get_object_or_404(FichierMedical, pk=fichier_id, dossier=dossier)
        fichier.delete()
        return Response(
            {"message": "Fichier supprimé."},
            status=status.HTTP_204_NO_CONTENT
        )


class RapportUpdateView(APIView):
    """
    PATCH /api/dossiers/{patient_id}/rapport/
    Le médecin met à jour ses notes et la conclusion du rapport.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id, doctor=get_doctor(request))
        dossier = get_object_or_404(Dossier, patient=patient)
        rapport = get_object_or_404(Rapport, dossier=dossier)
        return Response(RapportSerializer(rapport).data, status=status.HTTP_200_OK)

    def patch(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id, doctor=get_doctor(request))
        dossier = get_object_or_404(Dossier, patient=patient)
        rapport = get_object_or_404(Rapport, dossier=dossier)

        serializer = RapportSerializer(rapport, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)