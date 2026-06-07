from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from accounts.permissions import IsDoctor, IsDoctorOwner
from .models import Patient
from .serializers import (
    PatientListSerializer,
    PatientDetailSerializer,
    PatientCreateSerializer,
)


def get_doctor(request):
    return request.user.doctor_profile


class PatientListCreateView(APIView):
    """
    GET  /api/patients/      → liste des patients du médecin connecté
    POST /api/patients/      → ajouter un nouveau patient
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        patients = Patient.objects.filter(doctor=get_doctor(request))
        serializer = PatientListSerializer(patients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PatientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save(doctor=get_doctor(request))
        return Response(
            PatientDetailSerializer(patient).data,
            status=status.HTTP_201_CREATED,
        )


class PatientDetailView(APIView):
    """
    GET    /api/patients/{id}/   → détail d'un patient
    PUT    /api/patients/{id}/   → modifier un patient
    DELETE /api/patients/{id}/   → supprimer un patient
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_object(self, pk, doctor):
        return get_object_or_404(Patient, pk=pk, doctor=doctor)

    def get(self, request, pk):
        patient = self.get_object(pk, get_doctor(request))
        return Response(
            PatientDetailSerializer(patient).data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, pk):
        patient = self.get_object(pk, get_doctor(request))
        serializer = PatientCreateSerializer(patient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        return Response(
            PatientDetailSerializer(patient).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        patient = self.get_object(pk, get_doctor(request))
        patient.delete()
        return Response(
            {"message": "Patient supprimé avec succès."},
            status=status.HTTP_204_NO_CONTENT,
        )