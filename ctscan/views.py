from django.shortcuts import render

"""
views.py — App CtScan
Endpoints :
  POST   /api/ctscan/analyser/          → upload .mhd + .raw → analyse → nodules
  GET    /api/ctscan/                   → liste tous les scans du médecin connecté
  GET    /api/ctscan/<id>/              → détail d'un scan (avec nodules)
  GET    /api/ctscan/dossier/<id>/      → scans d'un dossier précis
  DELETE /api/ctscan/<id>/              → supprimer un scan
"""
import logging
import os
import tempfile

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dossiers.models import Dossier
from .models import CtScan, Nodule
from .serializers import (
    CtScanDetailSerializer,
    CtScanListSerializer,
    CtScanUploadSerializer,
)

logger = logging.getLogger(__name__)


# ── POST /api/ctscan/analyser/ ────────────────────────────────────────────────
class CtScanAnalyserView(APIView):
    """
    Upload d'un CT scan (.mhd + .raw) et lancement de l'analyse TiCNet.
    Synchrone : la réponse contient directement les nodules détectés.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CtScanUploadSerializer(data={
            'dossier_id':  request.data.get('dossier_id'),
            'fichier_mhd': request.FILES.get('fichier_mhd'),
            'fichier_raw': request.FILES.get('fichier_raw'),
        })

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Vérifier que le dossier appartient bien au médecin connecté
        dossier = get_object_or_404(
            Dossier,
            id=data['dossier_id'],
            patient__doctor__user=request.user,
        )

        # ── 1. Créer l'objet CtScan (statut EN_COURS) ────────────────────────
        ctscan = CtScan.objects.create(
            dossier     = dossier,
            fichier_mhd = data['fichier_mhd'],
            fichier_raw = data['fichier_raw'],
            statut      = CtScan.Statut.EN_COURS,
        )
        logger.info(f"[CtScan #{ctscan.id}] Analyse lancée pour dossier {dossier.id}")

        # ── 2. Pipeline preprocessing + inference ────────────────────────────
        tmp_dir = tempfile.mkdtemp(prefix='ctscan_upload_')
        try:
            # Écrire les fichiers uploadés sur disque (même répertoire requis par SimpleITK)
# Utiliser le nom ORIGINAL du fichier uploadé (avant renommage Django)
            mhd_filename = data['fichier_mhd'].name
            raw_filename = data['fichier_raw'].name

            mhd_path = os.path.join(tmp_dir, mhd_filename)
            raw_path = os.path.join(tmp_dir, raw_filename)

            # Remettre le curseur au début avant de lire
            data['fichier_mhd'].seek(0)
            data['fichier_raw'].seek(0)

            with open(mhd_path, 'wb') as f:
                for chunk in data['fichier_mhd'].chunks():
                    f.write(chunk)
            with open(raw_path, 'wb') as f:
                for chunk in data['fichier_raw'].chunks():
                    f.write(chunk)

            # Lancer l'analyse
            from .inference import analyser_ctscan
            resultat = analyser_ctscan(mhd_path, raw_path)

            # ── 3. Mettre à jour le CtScan avec les métadonnées ──────────────
            origin  = resultat['origin']
            spacing = resultat['spacing']

            ctscan.statut      = CtScan.Statut.TERMINE
            ctscan.origin_z    = origin[0]
            ctscan.origin_y    = origin[1]
            ctscan.origin_x    = origin[2]
            ctscan.spacing_z   = spacing[0]
            ctscan.spacing_y   = spacing[1]
            ctscan.spacing_x   = spacing[2]
            ctscan.duree_analyse = resultat['duree']
            ctscan.save()

            # ── 4. Créer les Nodules en base ──────────────────────────────────
            nodules_db = []
            for n in resultat['nodules']:
                nodule = Nodule.objects.create(
                    ctscan      = ctscan,
                    rang        = n['rang'],
                    monde_z     = n['monde']['z'],
                    monde_y     = n['monde']['y'],
                    monde_x     = n['monde']['x'],
                    voxel_z     = n['voxel']['z'],
                    voxel_y     = n['voxel']['y'],
                    voxel_x     = n['voxel']['x'],
                    diametre_mm = n['diametre_mm'],
                    probabilite = n['probabilite'],
                )
                nodules_db.append(nodule)

            logger.info(
                f"[CtScan #{ctscan.id}] ✅ Terminé — "
                f"{len(nodules_db)} nodules en {resultat['duree']}s"
            )

            # ── 5. Réponse ────────────────────────────────────────────────────
            return Response(
                CtScanDetailSerializer(ctscan).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            import traceback
            logger.error(f"[CtScan #{ctscan.id}] ❌ Erreur : {e}")
            traceback.print_exc()

            ctscan.statut        = CtScan.Statut.ERREUR
            ctscan.message_erreur = str(e)
            ctscan.save()

            return Response(
                {
                    "error":   "Erreur lors de l'analyse TiCNet",
                    "detail":  str(e),
                    "ctscan_id": ctscan.id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ── GET /api/ctscan/ ──────────────────────────────────────────────────────────
class CtScanListView(APIView):
    """Liste tous les scans du médecin connecté."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scans = CtScan.objects.filter(
            dossier__patient__doctor__user=request.user
        ).select_related('dossier__patient').prefetch_related('nodules')

        serializer = CtScanListSerializer(scans, many=True)
        return Response(serializer.data)


# ── GET /api/ctscan/<id>/ ─────────────────────────────────────────────────────
class CtScanDetailView(APIView):
    """Détail d'un scan avec tous ses nodules."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        ctscan = get_object_or_404(
            CtScan,
            pk=pk,
            dossier__patient__doctor__user=request.user,
        )
        return Response(CtScanDetailSerializer(ctscan).data)

    def delete(self, request, pk):
        ctscan = get_object_or_404(
            CtScan,
            pk=pk,
            dossier__patient__doctor__user=request.user,
        )
        ctscan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── GET /api/ctscan/dossier/<dossier_id>/ ────────────────────────────────────
class CtScanParDossierView(APIView):
    """Tous les scans d'un dossier précis."""
    permission_classes = [IsAuthenticated]

    def get(self, request, dossier_id):
        dossier = get_object_or_404(
            Dossier,
            id=dossier_id,
            patient__doctor__user=request.user,
        )
        scans = CtScan.objects.filter(
            dossier=dossier
        ).prefetch_related('nodules')

        serializer = CtScanDetailSerializer(scans, many=True)
        return Response(serializer.data)