# from django.shortcuts import render

# """
# views.py — App CtScan
# Endpoints :
#   POST   /api/ctscan/analyser/          → upload .mhd + .raw → analyse → nodules
#   GET    /api/ctscan/                   → liste tous les scans du médecin connecté
#   GET    /api/ctscan/<id>/              → détail d'un scan (avec nodules)
#   GET    /api/ctscan/dossier/<id>/      → scans d'un dossier précis
#   DELETE /api/ctscan/<id>/              → supprimer un scan
# """
# import logging
# import os
# import tempfile

# from django.shortcuts import get_object_or_404
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from rest_framework.views import APIView

# from dossiers.models import Dossier
# from .models import CtScan, Nodule
# from .serializers import (
#     CtScanDetailSerializer,
#     CtScanListSerializer,
#     CtScanUploadSerializer,
# )

# logger = logging.getLogger(__name__)


# # ── POST /api/ctscan/analyser/ ────────────────────────────────────────────────
# class CtScanAnalyserView(APIView):
#     """
#     Upload d'un CT scan (.mhd + .raw) et lancement de l'analyse TiCNet.
#     Synchrone : la réponse contient directement les nodules détectés.
#     """
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = CtScanUploadSerializer(data={
#             'dossier_id':  request.data.get('dossier_id'),
#             'fichier_mhd': request.FILES.get('fichier_mhd'),
#             'fichier_raw': request.FILES.get('fichier_raw'),
#         })

#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#         data = serializer.validated_data

#         # Vérifier que le dossier appartient bien au médecin connecté
#         dossier = get_object_or_404(
#             Dossier,
#             id=data['dossier_id'],
#             patient__doctor__user=request.user,
#         )

#         # ── 1. Créer l'objet CtScan (statut EN_COURS) ────────────────────────
#         ctscan = CtScan.objects.create(
#             dossier     = dossier,
#             fichier_mhd = data['fichier_mhd'],
#             fichier_raw = data['fichier_raw'],
#             statut      = CtScan.Statut.EN_COURS,
#         )
#         logger.info(f"[CtScan #{ctscan.id}] Analyse lancée pour dossier {dossier.id}")

#         # ── 2. Pipeline preprocessing + inference ────────────────────────────
#         tmp_dir = tempfile.mkdtemp(prefix='ctscan_upload_')
#         try:
#             # Écrire les fichiers uploadés sur disque (même répertoire requis par SimpleITK)
# # Utiliser le nom ORIGINAL du fichier uploadé (avant renommage Django)
#             mhd_filename = data['fichier_mhd'].name
#             raw_filename = data['fichier_raw'].name

#             mhd_path = os.path.join(tmp_dir, mhd_filename)
#             raw_path = os.path.join(tmp_dir, raw_filename)

#             # Remettre le curseur au début avant de lire
#             data['fichier_mhd'].seek(0)
#             data['fichier_raw'].seek(0)

#             with open(mhd_path, 'wb') as f:
#                 for chunk in data['fichier_mhd'].chunks():
#                     f.write(chunk)
#             with open(raw_path, 'wb') as f:
#                 for chunk in data['fichier_raw'].chunks():
#                     f.write(chunk)

#             # Lancer l'analyse
#             from .inference import analyser_ctscan
#             resultat = analyser_ctscan(mhd_path, raw_path)

#             # ── 3. Mettre à jour le CtScan avec les métadonnées ──────────────
#             origin  = resultat['origin']
#             spacing = resultat['spacing']

#             ctscan.statut      = CtScan.Statut.TERMINE
#             ctscan.origin_z    = origin[0]
#             ctscan.origin_y    = origin[1]
#             ctscan.origin_x    = origin[2]
#             ctscan.spacing_z   = spacing[0]
#             ctscan.spacing_y   = spacing[1]
#             ctscan.spacing_x   = spacing[2]
#             ctscan.duree_analyse = resultat['duree']
#             ctscan.save()

#             # ── 4. Créer les Nodules en base ──────────────────────────────────
#             nodules_db = []
#             for n in resultat['nodules']:
#                 nodule = Nodule.objects.create(
#                     ctscan      = ctscan,
#                     rang        = n['rang'],
#                     monde_z     = n['monde']['z'],
#                     monde_y     = n['monde']['y'],
#                     monde_x     = n['monde']['x'],
#                     voxel_z     = n['voxel']['z'],
#                     voxel_y     = n['voxel']['y'],
#                     voxel_x     = n['voxel']['x'],
#                     diametre_mm = n['diametre_mm'],
#                     probabilite = n['probabilite'],
#                 )
#                 nodules_db.append(nodule)

#             logger.info(
#                 f"[CtScan #{ctscan.id}] ✅ Terminé — "
#                 f"{len(nodules_db)} nodules en {resultat['duree']}s"
#             )

#             # ── 5. Réponse ────────────────────────────────────────────────────
#             return Response(
#                 CtScanDetailSerializer(ctscan).data,
#                 status=status.HTTP_201_CREATED,
#             )

#         except Exception as e:
#             import traceback
#             logger.error(f"[CtScan #{ctscan.id}] ❌ Erreur : {e}")
#             traceback.print_exc()

#             ctscan.statut        = CtScan.Statut.ERREUR
#             ctscan.message_erreur = str(e)
#             ctscan.save()

#             return Response(
#                 {
#                     "error":   "Erreur lors de l'analyse TiCNet",
#                     "detail":  str(e),
#                     "ctscan_id": ctscan.id,
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )
#         finally:
#             import shutil
#             import shutil
#             from django.conf import settings

# # Sauvegarder .mhd + .raw dans MEDIA_ROOT
#             media_ctscan = os.path.join(settings.MEDIA_ROOT, 'ctscan')
#             os.makedirs(media_ctscan, exist_ok=True)

#             mhd_final = os.path.join(media_ctscan, f'scan_{ctscan.id}.mhd')
#             raw_final  = os.path.join(media_ctscan, f'scan_{ctscan.id}.raw')

#             shutil.copy2(mhd_path, mhd_final)
#             shutil.copy2(raw_path, raw_final)

# # Stocker le chemin relatif dans le modèle
#             ctscan.fichier_mhd = f'ctscan/scan_{ctscan.id}.mhd'
#             ctscan.fichier_raw = f'ctscan/scan_{ctscan.id}.raw'
#             ctscan.save()
#             shutil.rmtree(tmp_dir, ignore_errors=True)


# # ── GET /api/ctscan/ ──────────────────────────────────────────────────────────
# class CtScanListView(APIView):
#     """Liste tous les scans du médecin connecté."""
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         scans = CtScan.objects.filter(
#             dossier__patient__doctor__user=request.user
#         ).select_related('dossier__patient').prefetch_related('nodules')

#         serializer = CtScanListSerializer(scans, many=True)
#         return Response(serializer.data)


# # ── GET /api/ctscan/<id>/ ─────────────────────────────────────────────────────
# class CtScanDetailView(APIView):
#     """Détail d'un scan avec tous ses nodules."""
#     permission_classes = [IsAuthenticated]

#     def get(self, request, pk):
#         ctscan = get_object_or_404(
#             CtScan,
#             pk=pk,
#             dossier__patient__doctor__user=request.user,
#         )
#         return Response(CtScanDetailSerializer(ctscan).data)

#     def delete(self, request, pk):
#         ctscan = get_object_or_404(
#             CtScan,
#             pk=pk,
#             dossier__patient__doctor__user=request.user,
#         )
#         ctscan.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)


# # ── GET /api/ctscan/dossier/<dossier_id>/ ────────────────────────────────────
# class CtScanParDossierView(APIView):
#     """Tous les scans d'un dossier précis."""
#     permission_classes = [IsAuthenticated]

#     def get(self, request, dossier_id):
#         dossier = get_object_or_404(
#             Dossier,
#             id=dossier_id,
#             patient__doctor__user=request.user,
#         )
#         scans = CtScan.objects.filter(
#             dossier=dossier
#         ).prefetch_related('nodules')

#         serializer = CtScanDetailSerializer(scans, many=True)
#         return Response(serializer.data)
    
    
    
    
# # ── POST /api/ctscan/analyser-dicom/ ─────────────────────────────────────────
# class CtScanAnalyserDicomView(APIView):
#     """
#     Upload d'un dossier DICOM (zippé) et lancement de l'analyse TiCNet.
#     Le .zip est extrait → converti en .mhd/.raw → pipeline inchangé.
#     """
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         from .serializers import CtScanDicomUploadSerializer
#         serializer = CtScanDicomUploadSerializer(data={
#             'dossier_id':  request.data.get('dossier_id'),
#             'fichier_zip': request.FILES.get('fichier_zip'),
#         })

#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#         data = serializer.validated_data

#         dossier = get_object_or_404(
#             Dossier,
#             id=data['dossier_id'],
#             patient__doctor__user=request.user,
#         )

#         ctscan = CtScan.objects.create(
#             dossier = dossier,
#             statut  = CtScan.Statut.EN_COURS,
#         )
#         logger.info(f"[CtScan #{ctscan.id}] Analyse DICOM lancée")

#         tmp_dir = tempfile.mkdtemp(prefix='dicom_upload_')
#         try:
#             import zipfile
#             import shutil
#             from .dicom_to_mhd import convert_dicom_to_mhd
#             from .inference import analyser_ctscan

#             # ── 1. Extraire le zip ───────────────────────────────────────────
#             zip_path = os.path.join(tmp_dir, 'upload.zip')
#             data['fichier_zip'].seek(0)
#             with open(zip_path, 'wb') as f:
#                 for chunk in data['fichier_zip'].chunks():
#                     f.write(chunk)

#             dicom_dir = os.path.join(tmp_dir, 'dicom')
#             os.makedirs(dicom_dir)
#             with zipfile.ZipFile(zip_path, 'r') as z:
#                 z.extractall(dicom_dir)

#             # ── 2. Trouver le dossier contenant les .dcm ─────────────────────
#             # (parfois le zip contient un sous-dossier)
#             dcm_folder = _find_dicom_folder(dicom_dir)

#             # ── 3. Conversion DICOM → .mhd + .raw ───────────────────────────
#             mhd_dir = os.path.join(tmp_dir, 'mhd')
#             os.makedirs(mhd_dir)
#             mhd_path, raw_path = convert_dicom_to_mhd(
#                 dicom_folder=dcm_folder,
#                 output_dir=mhd_dir,
#                 output_name="scan"
#             )

#             # ── 4. Pipeline TiCNet — IDENTIQUE à l'endpoint .mhd/.raw ────────
#             resultat = analyser_ctscan(mhd_path, raw_path)

#             # ── 5. Sauvegarder en base ───────────────────────────────────────
#             origin  = resultat['origin']
#             spacing = resultat['spacing']

#             ctscan.statut        = CtScan.Statut.TERMINE
#             ctscan.origin_z      = origin[0]
#             ctscan.origin_y      = origin[1]
#             ctscan.origin_x      = origin[2]
#             ctscan.spacing_z     = spacing[0]
#             ctscan.spacing_y     = spacing[1]
#             ctscan.spacing_x     = spacing[2]
#             ctscan.duree_analyse = resultat['duree']
#             ctscan.save()

#             for n in resultat['nodules']:
#                 Nodule.objects.create(
#                     ctscan      = ctscan,
#                     rang        = n['rang'],
#                     monde_z     = n['monde']['z'],
#                     monde_y     = n['monde']['y'],
#                     monde_x     = n['monde']['x'],
#                     voxel_z     = n['voxel']['z'],
#                     voxel_y     = n['voxel']['y'],
#                     voxel_x     = n['voxel']['x'],
#                     diametre_mm = n['diametre_mm'],
#                     probabilite = n['probabilite'],
#                 )

#             logger.info(
#                 f"[CtScan #{ctscan.id}] ✅ DICOM terminé — "
#                 f"{len(resultat['nodules'])} nodules en {resultat['duree']}s"
#             )

#             return Response(
#                 CtScanDetailSerializer(ctscan).data,
#                 status=status.HTTP_201_CREATED,
#             )

#         except Exception as e:
#             import traceback
#             logger.error(f"[CtScan #{ctscan.id}] ❌ Erreur DICOM : {e}")
#             traceback.print_exc()
#             ctscan.statut         = CtScan.Statut.ERREUR
#             ctscan.message_erreur = str(e)
#             ctscan.save()
#             return Response(
#                 {"error": "Erreur conversion DICOM", "detail": str(e), "ctscan_id": ctscan.id},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )
#         finally:
#             shutil.rmtree(tmp_dir, ignore_errors=True)


# def _find_dicom_folder(base_dir: str) -> str:
#     """
#     Trouve le dossier contenant les .dcm dans une arborescence extraite.
#     Gère le cas où le zip contient un sous-dossier racine.
#     """
#     # Chercher récursivement le premier dossier qui contient des .dcm
#     for root, dirs, files in os.walk(base_dir):
#         dcm_files = [f for f in files if f.lower().endswith('.dcm')]
#         if dcm_files:
#             return root
#     raise ValueError(f"Aucun fichier .dcm trouvé dans l'archive extraite : {base_dir}")



# # cette partie est pour afficher les  nodules dans le détail du scan, elle est à la fin du fichier serializers.py
# # ── GET /api/ctscan/<id>/slice/<z>/ ──────────────────────────────────────────
# # class CtScanSliceView(APIView):
# #     permission_classes = [IsAuthenticated]

# #     def get(self, request, pk, z):
# #         import base64, io
# #         import SimpleITK as sitk
# #         import numpy as np
# #         from PIL import Image

# #         ctscan = get_object_or_404(
# #             CtScan, pk=pk,
# #             dossier__patient__doctor__user=request.user
# #         )

# #         # ── Vérifier que le fichier .mhd existe ──────────────────────────────
# #         if not ctscan.fichier_mhd or not ctscan.fichier_mhd.name:
# #             return Response(
# #                 {"error": "fichier_mhd absent — ce scan a été uploadé via DICOM sans sauvegarde du .mhd"},
# #                 status=status.HTTP_400_BAD_REQUEST
# #             )

# #         mhd_path = ctscan.fichier_mhd.path

# #         if not os.path.isfile(mhd_path):
# #             return Response(
# #                 {"error": f"fichier .mhd introuvable sur disque : {mhd_path}"},
# #                 status=status.HTTP_404_NOT_FOUND
# #             )

# #         # ── Charger le volume ─────────────────────────────────────────────────
# #         try:
# #             image  = sitk.ReadImage(mhd_path)
# #             volume = sitk.GetArrayFromImage(image)  # (D, H, W)
# #         except Exception as e:
# #             return Response({"error": f"Erreur lecture .mhd : {str(e)}"}, status=500)

# #         view  = request.GET.get('view', 'axial')
# #         z_idx = int(z)

# #         if view == 'axial':
# #             total     = volume.shape[0]
# #             slice_arr = volume[z_idx] if 0 <= z_idx < total else None
# #         elif view == 'coronal':
# #             total     = volume.shape[1]
# #             slice_arr = volume[:, z_idx, :] if 0 <= z_idx < total else None
# #         elif view == 'sagittal':
# #             total     = volume.shape[2]
# #             slice_arr = volume[:, :, z_idx] if 0 <= z_idx < total else None
# #         else:
# #             return Response({"error": "view invalide (axial|coronal|sagittal)"}, status=400)

# #         if slice_arr is None:
# #             return Response(
# #                 {"error": f"index {z_idx} hors limites (total={total})"},
# #                 status=status.HTTP_400_BAD_REQUEST
# #             )

# #         # ── Fenêtrage pulmonaire + encodage PNG ───────────────────────────────
# #         slice_arr = np.clip(slice_arr, -1000, 400)
# #         slice_arr = ((slice_arr + 1000) / 1400 * 255).astype(np.uint8)

# #         img = Image.fromarray(slice_arr).convert("RGB")
# #         buf = io.BytesIO()
# #         img.save(buf, format="PNG")
# #         b64 = base64.b64encode(buf.getvalue()).decode()

# #         return Response({
# #             "slice_index": z_idx,
# #             "total_slices": total,
# #             "width":        slice_arr.shape[1],
# #             "height":       slice_arr.shape[0],
# #             "image_b64":    b64,
# #         })
# class CtScanSliceView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, pk, z):
#         import base64, io
#         import SimpleITK as sitk
#         import numpy as np
#         from PIL import Image

#         ctscan = get_object_or_404(
#             CtScan, pk=pk,
#             dossier__patient__doctor__user=request.user
#         )

#         # ── Vérifier que le fichier .mhd existe ──────────────────────────────
#         if not ctscan.fichier_mhd or not ctscan.fichier_mhd.name:
#             return Response(
#                 {"error": "fichier_mhd absent — ce scan a été uploadé via DICOM sans sauvegarde du .mhd"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         mhd_path = ctscan.fichier_mhd.path

#         if not os.path.isfile(mhd_path):
#             return Response(
#                 {"error": f"fichier .mhd introuvable sur disque : {mhd_path}"},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         # ── Charger le volume ─────────────────────────────────────────────────
#         try:
#             image  = sitk.ReadImage(mhd_path)
#             volume = sitk.GetArrayFromImage(image)  # (D, H, W)
#         except Exception as e:
#             return Response({"error": f"Erreur lecture .mhd : {str(e)}"}, status=500)

#         view  = request.GET.get('view', 'axial')
#         z_idx = int(z)

#         if view == 'axial':
#             total     = volume.shape[0]
#             slice_arr = volume[z_idx] if 0 <= z_idx < total else None
#         elif view == 'coronal':
#             total     = volume.shape[1]
#             slice_arr = volume[:, z_idx, :] if 0 <= z_idx < total else None
#         elif view == 'sagittal':
#             total     = volume.shape[2]
#             slice_arr = volume[:, :, z_idx] if 0 <= z_idx < total else None
#         else:
#             return Response({"error": "view invalide (axial|coronal|sagittal)"}, status=400)

#         if slice_arr is None:
#             return Response(
#                 {"error": f"index {z_idx} hors limites (total={total})"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # ── Fenêtrage pulmonaire + encodage PNG ───────────────────────────────
#         slice_arr = np.clip(slice_arr, -1000, 400)
#         slice_arr = ((slice_arr + 1000) / 1400 * 255).astype(np.uint8)

#         img = Image.fromarray(slice_arr).convert("RGB")
#         buf = io.BytesIO()
#         img.save(buf, format="PNG")
#         b64 = base64.b64encode(buf.getvalue()).decode()

#         return Response({
#             "slice_index": z_idx,
#             "total_slices": total,
#             "width":        slice_arr.shape[1],
#             "height":       slice_arr.shape[0],
#             "image_b64":    b64,
#         })

from django.shortcuts import render

"""
views.py — App CtScan
"""

import base64
import io
import logging
import os
import shutil
import tempfile
import zipfile

import numpy as np
import SimpleITK as sitk
from PIL import Image

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dossiers.models import Dossier
from .dicom_to_mhd import convert_dicom_to_mhd
from .inference import analyser_ctscan
from .models import CtScan, Nodule
from .serializers import (
    CtScanDetailSerializer,
    CtScanDicomUploadSerializer,
    CtScanListSerializer,
    CtScanUploadSerializer,
)

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024 * 1024


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_scan_files(ctscan: CtScan, mhd_path: str, raw_path: str) -> None:
    media_ctscan = os.path.join(settings.MEDIA_ROOT, 'ctscan')
    os.makedirs(media_ctscan, exist_ok=True)

    mhd_dest = os.path.join(media_ctscan, f'scan_{ctscan.id}.mhd')
    raw_dest  = os.path.join(media_ctscan, f'scan_{ctscan.id}.raw')

    shutil.copy2(mhd_path, mhd_dest)
    shutil.copy2(raw_path, raw_dest)

    # ✅ Forcer l'assignation correcte du chemin relatif
    CtScan.objects.filter(pk=ctscan.pk).update(
        fichier_mhd=f'ctscan/scan_{ctscan.id}.mhd',
        fichier_raw=f'ctscan/scan_{ctscan.id}.raw',
    )
    # Rafraîchir l'instance en mémoire
    ctscan.refresh_from_db()


def _create_nodules(ctscan: CtScan, nodules_data: list) -> list:
    nodules_db = []
    for n in nodules_data:
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
    return nodules_db


def _apply_resultat_to_ctscan(ctscan: CtScan, resultat: dict) -> None:
    origin  = resultat['origin']
    spacing = resultat['spacing']

    ctscan.statut        = CtScan.Statut.TERMINE
    ctscan.origin_z      = origin[0]
    ctscan.origin_y      = origin[1]
    ctscan.origin_x      = origin[2]
    ctscan.spacing_z     = spacing[0]
    ctscan.spacing_y     = spacing[1]
    ctscan.spacing_x     = spacing[2]
    ctscan.duree_analyse = resultat['duree']


def _find_dicom_folder(base_dir: str) -> str:
    dicom_extensions = ('.dcm', '.dicom')
    for root, dirs, files in os.walk(base_dir):
        if any(f.lower().endswith(dicom_extensions) for f in files):
            return root
    raise ValueError(
        f"Aucun fichier .dcm/.dicom trouvé dans l'archive extraite : {base_dir}"
    )


def _check_file_size(file_obj, label: str):
    if file_obj.size > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(
            f"{label} trop volumineux : {file_obj.size / (1024**3):.2f} Go "
            f"(max {MAX_UPLOAD_SIZE_BYTES // (1024**3)} Go)"
        )


# ── POST /api/ctscan/analyser/ ────────────────────────────────────────────────
class CtScanAnalyserView(APIView):
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

        try:
            _check_file_size(data['fichier_mhd'], 'fichier_mhd')
            _check_file_size(data['fichier_raw'], 'fichier_raw')
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        dossier = get_object_or_404(
            Dossier,
            id=data['dossier_id'],
            patient__doctor__user=request.user,
        )

        # Créer le scan sans fichiers (affectés après analyse via _save_scan_files)
        ctscan = CtScan.objects.create(
            dossier = dossier,
            statut  = CtScan.Statut.EN_COURS,
        )
        logger.info(f"[CtScan #{ctscan.id}] Analyse MHD lancée pour dossier {dossier.id}")

        tmp_dir = tempfile.mkdtemp(prefix='ctscan_upload_')

        try:
            # ── 1. Écrire les fichiers uploadés sur disque ───────────────────
            mhd_filename = data['fichier_mhd'].name
            raw_filename = data['fichier_raw'].name

            mhd_path = os.path.join(tmp_dir, mhd_filename)
            raw_path = os.path.join(tmp_dir, raw_filename)

            data['fichier_mhd'].seek(0)
            data['fichier_raw'].seek(0)

            with open(mhd_path, 'wb') as f:
                for chunk in data['fichier_mhd'].chunks():
                    f.write(chunk)
            with open(raw_path, 'wb') as f:
                for chunk in data['fichier_raw'].chunks():
                    f.write(chunk)

            # ── 2. Pipeline preprocessing + inference ────────────────────────
            resultat = analyser_ctscan(mhd_path, raw_path)

            # ── 3. Appliquer les métadonnées sur l'instance ──────────────────
            _apply_resultat_to_ctscan(ctscan, resultat)

            # ── 4. Sauvegarder les fichiers + persister les chemins en base ──
            _save_scan_files(ctscan, mhd_path, raw_path)

            # ── 5. Sauvegarder les métadonnées (fichier_mhd/raw déjà en base)─
            ctscan.save(update_fields=[
                'statut',
                'origin_z', 'origin_y', 'origin_x',
                'spacing_z', 'spacing_y', 'spacing_x',
                'duree_analyse',
            ])

            # ── 6. Créer les Nodules ──────────────────────────────────────────
            nodules_db = _create_nodules(ctscan, resultat['nodules'])

            logger.info(
                f"[CtScan #{ctscan.id}] ✅ Terminé — "
                f"{len(nodules_db)} nodules en {resultat['duree']}s"
            )

            return Response(
                CtScanDetailSerializer(ctscan).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.exception(f"[CtScan #{ctscan.id}] ❌ Erreur analyse MHD")
            ctscan.statut         = CtScan.Statut.ERREUR
            ctscan.message_erreur = str(e)
            ctscan.save(update_fields=['statut', 'message_erreur'])
            return Response(
                {
                    "error":     "Erreur lors de l'analyse TiCNet",
                    "detail":    str(e),
                    "ctscan_id": ctscan.id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ── GET /api/ctscan/ ──────────────────────────────────────────────────────────
class CtScanListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scans = (
            CtScan.objects
            .filter(dossier__patient__doctor__user=request.user)
            .select_related('dossier__patient')
            .prefetch_related('nodules')
            .order_by('-id')
        )
        return Response(CtScanListSerializer(scans, many=True).data)


# ── GET /api/ctscan/<id>/ — DELETE /api/ctscan/<id>/ ─────────────────────────
class CtScanDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_ctscan(self, request, pk):
        return get_object_or_404(
            CtScan,
            pk=pk,
            dossier__patient__doctor__user=request.user,
        )

    def get(self, request, pk):
        return Response(CtScanDetailSerializer(self._get_ctscan(request, pk)).data)

    def delete(self, request, pk):
        self._get_ctscan(request, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── GET /api/ctscan/dossier/<dossier_id>/ ────────────────────────────────────
class CtScanParDossierView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, dossier_id):
        dossier = get_object_or_404(
            Dossier,
            id=dossier_id,
            patient__doctor__user=request.user,
        )
        scans = (
            CtScan.objects
            .filter(dossier=dossier)
            .prefetch_related('nodules')
            .order_by('-id')
        )
        return Response(CtScanDetailSerializer(scans, many=True).data)


# ── POST /api/ctscan/analyser-dicom/ ─────────────────────────────────────────
class CtScanAnalyserDicomView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CtScanDicomUploadSerializer(data={
            'dossier_id':  request.data.get('dossier_id'),
            'fichier_zip': request.FILES.get('fichier_zip'),
        })

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            _check_file_size(data['fichier_zip'], 'fichier_zip')
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        dossier = get_object_or_404(
            Dossier,
            id=data['dossier_id'],
            patient__doctor__user=request.user,
        )

        ctscan = CtScan.objects.create(
            dossier = dossier,
            statut  = CtScan.Statut.EN_COURS,
        )
        logger.info(f"[CtScan #{ctscan.id}] Analyse DICOM lancée")

        tmp_dir = tempfile.mkdtemp(prefix='dicom_upload_')

        try:
            # ── 1. Écrire et extraire le zip ─────────────────────────────────
            zip_path = os.path.join(tmp_dir, 'upload.zip')
            data['fichier_zip'].seek(0)
            with open(zip_path, 'wb') as f:
                for chunk in data['fichier_zip'].chunks():
                    f.write(chunk)

            dicom_dir = os.path.join(tmp_dir, 'dicom')
            os.makedirs(dicom_dir)
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(dicom_dir)

            # ── 2. Trouver le dossier contenant les .dcm ─────────────────────
            dcm_folder = _find_dicom_folder(dicom_dir)

            # ── 3. Conversion DICOM → .mhd + .raw ───────────────────────────
            mhd_dir = os.path.join(tmp_dir, 'mhd')
            os.makedirs(mhd_dir)
            mhd_path, raw_path = convert_dicom_to_mhd(
                dicom_folder = dcm_folder,
                output_dir   = mhd_dir,
                output_name  = "scan",
            )

            # ── 4. Pipeline TiCNet ────────────────────────────────────────────
            resultat = analyser_ctscan(mhd_path, raw_path)

            # ── 5. Appliquer les métadonnées sur l'instance ──────────────────
            _apply_resultat_to_ctscan(ctscan, resultat)

            # ── 6. Sauvegarder les fichiers + persister les chemins en base ──
            _save_scan_files(ctscan, mhd_path, raw_path)

            # ── 7. Sauvegarder les métadonnées (fichier_mhd/raw déjà en base)─
            ctscan.save(update_fields=[
                'statut',
                'origin_z', 'origin_y', 'origin_x',
                'spacing_z', 'spacing_y', 'spacing_x',
                'duree_analyse',
            ])

            # ── 8. Créer les Nodules ──────────────────────────────────────────
            nodules_db = _create_nodules(ctscan, resultat['nodules'])

            logger.info(
                f"[CtScan #{ctscan.id}] ✅ DICOM terminé — "
                f"{len(nodules_db)} nodules en {resultat['duree']}s"
            )

            return Response(
                CtScanDetailSerializer(ctscan).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.exception(f"[CtScan #{ctscan.id}] ❌ Erreur DICOM")
            ctscan.statut         = CtScan.Statut.ERREUR
            ctscan.message_erreur = str(e)
            ctscan.save(update_fields=['statut', 'message_erreur'])
            return Response(
                {
                    "error":     "Erreur conversion DICOM",
                    "detail":    str(e),
                    "ctscan_id": ctscan.id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ── GET /api/ctscan/<id>/slice/<z>/ ──────────────────────────────────────────
class CtScanSliceView(APIView):
    permission_classes = [IsAuthenticated]

    WIN_MIN   = -1000
    WIN_MAX   =  400
    WIN_RANGE = WIN_MAX - WIN_MIN

    def get(self, request, pk, z):
        ctscan = get_object_or_404(
            CtScan,
            pk=pk,
            dossier__patient__doctor__user=request.user,
        )

        if not ctscan.fichier_mhd or not ctscan.fichier_mhd.name:
            return Response(
                {"error": "fichier_mhd absent pour ce scan"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mhd_path = ctscan.fichier_mhd.path
        if not os.path.isfile(mhd_path):
            return Response(
                {"error": f"fichier .mhd introuvable sur disque : {mhd_path}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Valider l'index z ─────────────────────────────────────────────────
        try:
            z_idx = int(z)
        except ValueError:
            return Response(
                {"error": "Index de slice invalide, un entier est attendu"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Charger le volume ─────────────────────────────────────────────────
        try:
            image  = sitk.ReadImage(mhd_path)
            volume = sitk.GetArrayFromImage(image)
        except Exception as e:
            logger.exception(f"[CtScan #{ctscan.id}] Erreur lecture .mhd")
            return Response(
                {"error": f"Erreur lecture .mhd : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Extraire la slice selon la vue demandée ───────────────────────────
        view = request.GET.get('view', 'axial')

        axis_map = {
            'axial':    (0, lambda v, i: v[i]),
            'coronal':  (1, lambda v, i: v[:, i, :]),
            'sagittal': (2, lambda v, i: v[:, :, i]),
        }

        if view not in axis_map:
            return Response(
                {"error": "Paramètre 'view' invalide. Valeurs acceptées : axial, coronal, sagittal"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        axis, extractor = axis_map[view]
        total = volume.shape[axis]

        if not (0 <= z_idx < total):
            return Response(
                {"error": f"Index {z_idx} hors limites (0–{total - 1})"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        slice_arr = extractor(volume, z_idx)

        # ── Fenêtrage pulmonaire + encodage PNG ───────────────────────────────
        slice_arr = np.clip(slice_arr, self.WIN_MIN, self.WIN_MAX)
        slice_arr = ((slice_arr - self.WIN_MIN) / self.WIN_RANGE * 255).astype(np.uint8)

        img = Image.fromarray(slice_arr).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        return Response({
            "slice_index":  z_idx,
            "total_slices": total,
            "width":        slice_arr.shape[1],
            "height":       slice_arr.shape[0],
            "view":         view,
            "image_b64":    b64,
        })