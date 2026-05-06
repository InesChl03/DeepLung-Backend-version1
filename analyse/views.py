import os
import traceback

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDoctor
from dossiers.models import Dossier, FichierMedical
from patients.models import Patient
from .models import Analyse, Nodule
from .serializers import AnalyseSerializer, AnalyseListSerializer
from .inference import run_inference


def get_doctor(request):
    return request.user.doctor_profile


class LancerAnalyseView(APIView):
    """
    POST /api/analyse/{patient_id}/fichiers/{fichier_id}/lancer/

    Lance l'analyse IA TiCNet sur un fichier médical du dossier.
    Le fichier doit déjà être uploadé dans le dossier du patient.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def post(self, request, patient_id, fichier_id):
        # Vérifie que le patient appartient au médecin connecté
        patient = get_object_or_404(
            Patient, pk=patient_id, doctor=get_doctor(request)
        )
        dossier = get_object_or_404(Dossier, patient=patient)
        fichier = get_object_or_404(FichierMedical, pk=fichier_id, dossier=dossier)

        # Crée l'entrée analyse avec statut EN_COURS
        analyse = Analyse.objects.create(
            dossier=dossier,
            fichier_medical=fichier,
            statut=Analyse.Statut.EN_COURS,
        )

        try:
            # Chemin du modèle .pth
            pth_path = getattr(settings, 'TICNET_MODEL_PATH', None)
            if not pth_path or not os.path.exists(pth_path):
                raise FileNotFoundError(
                    f"Modèle TiCNet introuvable. "
                    f"Vérifiez TICNET_MODEL_PATH dans settings.py : {pth_path}"
                )

            # Chemin du fichier CT uploadé
            ct_filepath = fichier.fichier.path

            # Dossier de sortie pour les slices PNG
            output_dir = os.path.join(
                settings.MEDIA_ROOT, 'analyses', f'analyse_{analyse.pk}'
            )

            # Lance l'inférence
            results = run_inference(pth_path, ct_filepath, output_dir)

            # Sauvegarde les résultats dans la base
            analyse.statut          = Analyse.Statut.TERMINE
            analyse.nodule_count    = results['nodule_count']
            analyse.max_probability = results['max_probability']
            analyse.slices_dir      = results['slices_dir']
            analyse.niveau_risque   = _get_global_risk(results['nodules'])
            analyse.save()

            # Sauvegarde chaque nodule détecté
            for n in results['nodules']:
                Nodule.objects.create(
                    analyse=analyse,
                    coordX=n['coordX'],
                    coordY=n['coordY'],
                    coordZ=n['coordZ'],
                    diameter_mm=n['diameter_mm'],
                    probability=n['probability'],
                    risk=n['risk'],
                )

            return Response(
                AnalyseSerializer(analyse, context={'request': request}).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            analyse.statut = Analyse.Statut.ECHOUE
            analyse.erreur = traceback.format_exc()
            analyse.save()
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AnalyseDetailView(APIView):
    """
    GET /api/analyse/{patient_id}/resultats/
    Retourne toutes les analyses du dossier du patient.

    GET /api/analyse/{patient_id}/resultats/{analyse_id}/
    Retourne le détail d'une analyse spécifique.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request, patient_id, analyse_id=None):
        patient = get_object_or_404(
            Patient, pk=patient_id, doctor=get_doctor(request)
        )
        dossier = get_object_or_404(Dossier, patient=patient)

        if analyse_id:
            analyse = get_object_or_404(Analyse, pk=analyse_id, dossier=dossier)
            return Response(
                AnalyseSerializer(analyse, context={'request': request}).data
            )

        analyses = Analyse.objects.filter(dossier=dossier)
        return Response(
            AnalyseListSerializer(analyses, many=True).data
        )


class SlicesListView(APIView):
    """
    GET /api/analyse/{patient_id}/resultats/{analyse_id}/slices/
    Retourne les URLs des slices PNG générées par la visualisation.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request, patient_id, analyse_id):
        patient = get_object_or_404(
            Patient, pk=patient_id, doctor=get_doctor(request)
        )
        dossier = get_object_or_404(Dossier, patient=patient)
        analyse = get_object_or_404(Analyse, pk=analyse_id, dossier=dossier)

        if not analyse.slices_dir or not os.path.exists(analyse.slices_dir):
            return Response(
                {"error": "Aucune visualisation disponible pour cette analyse."},
                status=status.HTTP_404_NOT_FOUND,
            )

        slices = []
        for fname in sorted(os.listdir(analyse.slices_dir)):
            if fname.endswith('.png'):
                # Construit l'URL relative /media/analyses/...
                rel_path = os.path.relpath(
                    os.path.join(analyse.slices_dir, fname),
                    settings.MEDIA_ROOT
                ).replace('\\', '/')
                slices.append({
                    'filename': fname,
                    'url': request.build_absolute_uri(
                        settings.MEDIA_URL + rel_path
                    ),
                })

        return Response({
            'analyse_id':   analyse.pk,
            'slice_count':  len(slices),
            'slices':       slices,
        })


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_global_risk(nodules: list) -> str:
    """Retourne le niveau de risque global basé sur le nodule le plus dangereux."""
    if not nodules:
        return "AUCUN"
    risks = [n['risk'] for n in nodules]
    priority = ["CRITIQUE", "ELEVE", "MODERE", "FAIBLE"]
    for r in priority:
        if r in risks:
            return r
    return "FAIBLE"