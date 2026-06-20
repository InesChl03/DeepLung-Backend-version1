from django.shortcuts import render

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ctscan.models import CtScan
from classification.models import NoduleClassification
from classification.serializers import NoduleClassificationSerializer
from classification.classifier import classify_scan

logger = logging.getLogger(__name__)


# =============================================================================
# GET /api/classification/scan/<scan_id>/
# Retourne les résultats de classification d'un scan.
# Si pas encore classifié → lance la classification automatiquement.
# Auth : token JWT (IsAuthenticated) — pas de filtrage par médecin pour l'instant.
# =============================================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_classification(request, scan_id):
    """
    Retourne les classifications de tous les nodules d'un scan.

    Réponse :
    {
        "scan_id": 66,
        "statut": "TERMINE",
        "nb_nodules": 2,
        "classifications": [
            {
                "id": 1,
                "nodule_id_ticnet": 274,
                "rang": 1,
                "diametre_mm": 29.09,
                "prob_detection": 0.9836,
                "label": 1,
                "label_str": "Maligne",
                "proba_maligne": 0.9995,
                "proba_benigne": 0.0005,
                ...
            }
        ]
    }
    """
    try:
        scan = CtScan.objects.get(id=scan_id)
    except CtScan.DoesNotExist:
        return Response(
            {"error": f"Scan {scan_id} introuvable."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Si TiCNet n'a pas encore terminé
    if scan.statut != CtScan.Statut.TERMINE:
        return Response(
            {
                "scan_id": scan_id,
                "statut": scan.statut,
                "message": "L'analyse TiCNet n'est pas encore terminée.",
                "classifications": [],
            },
            status=status.HTTP_202_ACCEPTED
        )

    # Si pas encore classifié → lancer maintenant (flux automatique)
    existing = NoduleClassification.objects.filter(scan=scan)
    if not existing.exists():
        logger.info(f"[API] Scan {scan_id} — lancement classification...")
        try:
            classify_scan(scan)
        except Exception as e:
            logger.error(f"[API] Erreur classification scan {scan_id} : {e}")
            return Response(
                {"error": f"Erreur lors de la classification : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        existing = NoduleClassification.objects.filter(scan=scan)

    serializer = NoduleClassificationSerializer(existing, many=True)
    return Response({
        "scan_id":         scan_id,
        "statut":          scan.statut,
        "nb_nodules":      existing.count(),
        "classifications": serializer.data,
    })


# =============================================================================
# POST /api/classification/scan/<scan_id>/relancer/
# Force une re-classification (utile si le modèle a été mis à jour).
# =============================================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def relancer_classification(request, scan_id):
    """
    Supprime les anciens résultats et relance la classification.
    """
    try:
        scan = CtScan.objects.get(id=scan_id)
    except CtScan.DoesNotExist:
        return Response(
            {"error": f"Scan {scan_id} introuvable."},
            status=status.HTTP_404_NOT_FOUND
        )

    if scan.statut != CtScan.Statut.TERMINE:
        return Response(
            {"error": "Le scan TiCNet n'est pas encore terminé."},
            status=status.HTTP_400_BAD_REQUEST
        )

    deleted, _ = NoduleClassification.objects.filter(scan=scan).delete()
    logger.info(f"[API] Scan {scan_id} — {deleted} classification(s) supprimée(s)")

    try:
        results = classify_scan(scan)
    except Exception as e:
        return Response(
            {"error": f"Erreur : {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    serializer = NoduleClassificationSerializer(results, many=True)
    return Response({
        "scan_id":         scan_id,
        "nb_nodules":      len(results),
        "classifications": serializer.data,
    }, status=status.HTTP_200_OK)