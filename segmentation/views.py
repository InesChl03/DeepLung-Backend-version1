# """
# segmentation/views.py
# POST /api/segmentation/segment/  — upload ZIP DICOM → segmentation + stockage BDD
# GET  /api/segmentation/scan/<scan_id>/  — résultats d'un scan depuis la BDD
# """

# import os
# import uuid
# import zipfile
# import logging
# from pathlib import Path

# from django.conf import settings
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods

# from ctscan.models import CtScan, Nodule
# from .models import NoduleSegmentation
# from .utils.inference import run_inference

# logger   = logging.getLogger(__name__)
# MEDIA_ROOT = Path(settings.MEDIA_ROOT)
# MEDIA_URL  = getattr(settings, 'MEDIA_URL', '/media/')


# def _to_url(abs_path):
#     """Convertit chemin absolu → URL Django."""
#     if not abs_path:
#         return ''
#     try:
#         rel = Path(abs_path).relative_to(MEDIA_ROOT)
#         return MEDIA_URL + str(rel).replace('\\', '/')
#     except Exception:
#         return str(abs_path)


# def _save_segmentations(scan, results):
#     """
#     Sauvegarde chaque nodule segmenté en base.
#     On fait correspondre nodule_id_seg (rang dans results, 1-based)
#     avec le Nodule TiCNet via son rang (Nodule.rang).
#     """
#     nodules_ticnet = list(
#         Nodule.objects.filter(ctscan=scan).order_by('rang')
#     )

#     for idx, n in enumerate(results):
#         # Lien avec le nodule TiCNet : on prend le même rang
#         nodule_id_ticnet = nodules_ticnet[idx].id if idx < len(nodules_ticnet) else None
#         if nodule_id_ticnet is None:
#             logger.warning(f"Pas de nodule TiCNet correspondant pour rang {idx+1}")
#             continue

#         NoduleSegmentation.objects.update_or_create(
#             scan=scan,
#             nodule_id_ticnet=nodule_id_ticnet,
#             defaults={
#                 'rpn_score':          n['rpn_score'],
#                 'center_mm':          n['center_mm'],
#                 'center_voxel':       n['center_voxel'],
#                 'diam_ticnet_mm':     n['diam_ticnet'],
#                 'diam_seg_mm':        n['diam_seg'],
#                 'volume_mm3':         n['volume_mm3'],
#                 'n_voxels':           n['n_voxels'],
#                 'ct_image_path':      n.get('ct_url', ''),
#                 'mask_npy_path':      n.get('mask_npy', ''),
#                 'mask_image_path':    n.get('mask_image', ''),
#                 'contour_image_path': n.get('contour_url', ''),
#                 'mesh_json_path':     n.get('mesh_url', '') or '',
#             }
#         )
#         logger.info(f"✓ NoduleSegmentation sauvegardée — scan={scan.id} nodule_ticnet={nodule_id_ticnet}")


# @csrf_exempt
# @require_http_methods(['POST'])
# def segment_nodules(request):
#     """
#     POST /api/segmentation/segment/
#     Body (multipart/form-data) :
#         dicom_file : ZIP contenant les .dcm
#         scan_id    : ID du CtScan en base (obligatoire pour le lien BDD)
#     """
#     # ── Vérifications ────────────────────────────────────────────────────────
#     if 'dicom_file' not in request.FILES:
#         return JsonResponse({
#             'success': False,
#             'error': "Champ 'dicom_file' manquant."
#         }, status=400)

#     scan_id = request.POST.get('scan_id')
#     if not scan_id:
#         return JsonResponse({
#             'success': False,
#             'error': "Champ 'scan_id' manquant."
#         }, status=400)

#     try:
#         scan = CtScan.objects.get(pk=scan_id)
#     except CtScan.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'error': f"CtScan id={scan_id} introuvable."
#         }, status=404)

#     # ── Extraction DICOM ─────────────────────────────────────────────────────
#     uploaded = request.FILES['dicom_file']
#     job_id   = str(uuid.uuid4())[:8]
#     job_dir  = MEDIA_ROOT / 'segmentation' / f'job_{job_id}'
#     dcm_dir  = job_dir / 'dicom'
#     out_dir  = job_dir / 'output'
#     dcm_dir.mkdir(parents=True, exist_ok=True)
#     out_dir.mkdir(parents=True, exist_ok=True)

#     try:
#         zip_path = job_dir / 'upload.zip'
#         with open(zip_path, 'wb') as f:
#             for chunk in uploaded.chunks():
#                 f.write(chunk)

#         with zipfile.ZipFile(zip_path, 'r') as zf:
#             for member in zf.namelist():
#                 if member.lower().endswith('.dcm'):
#                     fname = os.path.basename(member)
#                     if not fname:
#                         continue
#                     with zf.open(member) as src, open(dcm_dir / fname, 'wb') as dst:
#                         dst.write(src.read())

#     except Exception as e:
#         logger.error(f"Erreur extraction ZIP : {e}")
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)

#     dcm_files = list(dcm_dir.glob('*.dcm'))
#     if len(dcm_files) < 10:
#         return JsonResponse({
#             'success': False,
#             'error': f"Seulement {len(dcm_files)} fichiers .dcm trouvés (min 10)."
#         }, status=400)

#     # ── Inférence ────────────────────────────────────────────────────────────
#     try:
#         result = run_inference(
#             dicom_dir=str(dcm_dir),
#             out_dir=str(out_dir),
#             seuil_detection=0.5,
#             seuil_segmentation=0.5,
#             min_diameter_mm=3.0,
#         )
#     except ValueError as e:
#         return JsonResponse({'success': False, 'error': str(e)}, status=400)
#     except Exception as e:
#         logger.error(f"Erreur inférence : {e}", exc_info=True)
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)

#     # ── Stockage BDD ─────────────────────────────────────────────────────────
#     if result['total'] > 0:
#         try:
#             _save_segmentations(scan, result['nodules'])
#         except Exception as e:
#             logger.error(f"Erreur sauvegarde BDD : {e}", exc_info=True)
#             # non-bloquant : on retourne quand même le résultat

#     # ── Réponse JSON ─────────────────────────────────────────────────────────
#     nodules_resp = []
#     for n in result['nodules']:
#         nodules_resp.append({
#             'nodule_id':    n['nodule_id'],
#             'rpn_score':    n['rpn_score'],
#             'center_mm':    n['center_mm'],
#             'center_voxel': n['center_voxel'],
#             'diam_ticnet':  n['diam_ticnet'],
#             'diam_seg':     n['diam_seg'],
#             'volume_mm3':   n['volume_mm3'],
#             'n_voxels':     n['n_voxels'],
#             'ct_url':           _to_url(n.get('ct_url')),
#             'mask_image_url':   _to_url(n.get('mask_image')),
#             'contour_url':      _to_url(n.get('contour_url')),
#             'mesh_url':         _to_url(n.get('mesh_url')),
#         })

#     return JsonResponse({
#         'success': True,
#         'job_id':  job_id,
#         'scan_id': scan.id,
#         'total':   result['total'],
#         'duree':   result.get('duree', 0),
#         'message': result.get('message', ''),
#         'nodules': nodules_resp,
#     }, status=200)


# @require_http_methods(['GET'])
# def get_scan_segmentations(request, scan_id):
#     """
#     GET /api/segmentation/scan/<scan_id>/
#     Retourne toutes les segmentations d'un scan depuis la BDD.
#     """
#     try:
#         scan = CtScan.objects.get(pk=scan_id)
#     except CtScan.DoesNotExist:
#         return JsonResponse({'success': False, 'error': 'Scan introuvable.'}, status=404)

#     segs = NoduleSegmentation.objects.filter(scan=scan).order_by('nodule_id_ticnet')

#     nodules_resp = []
#     for s in segs:
#         nodules_resp.append({
#             'nodule_id_ticnet':  s.nodule_id_ticnet,
#             'rpn_score':         s.rpn_score,
#             'center_mm':         s.center_mm,
#             'center_voxel':      s.center_voxel,
#             'diam_ticnet_mm':    s.diam_ticnet_mm,
#             'diam_seg_mm':       s.diam_seg_mm,
#             'volume_mm3':        s.volume_mm3,
#             'n_voxels':          s.n_voxels,
#             'ct_url':            _to_url(s.ct_image_path),
#             'mask_image_url':    _to_url(s.mask_image_path),
#             'contour_url':       _to_url(s.contour_image_path),
#             'mesh_url':          _to_url(s.mesh_json_path),
#             'created_at':        s.created_at.isoformat(),
#         })

#     return JsonResponse({
#         'success': True,
#         'scan_id': scan.id,
#         'total':   len(nodules_resp),
#         'nodules': nodules_resp,
#     })
"""
segmentation/views.py
POST /api/segmentation/segment/              — upload ZIP DICOM → segmentation + stockage BDD (nouveau scan)
POST /api/segmentation/segment-existing/<scan_id>/ — segmentation à partir d'un scan déjà existant (.mhd stocké)
GET  /api/segmentation/scan/<scan_id>/        — résultats d'un scan depuis la BDD
"""

import os
import uuid
import zipfile
import logging
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ctscan.models import CtScan
from .models import NoduleSegmentation
from .utils.inference import run_inference, run_inference_existing_scan

logger   = logging.getLogger(__name__)
MEDIA_ROOT = Path(settings.MEDIA_ROOT)
MEDIA_URL  = getattr(settings, 'MEDIA_URL', '/media/')


def _to_url(abs_path):
    """Convertit chemin absolu → URL Django."""
    if not abs_path:
        return ''
    try:
        rel = Path(abs_path).relative_to(MEDIA_ROOT)
        return MEDIA_URL + str(rel).replace('\\', '/')
    except Exception:
        return str(abs_path)


def _save_segmentations(scan, results):
    """
    Sauvegarde chaque nodule segmenté en base.

    nodule_id_ticnet est l'identifiant LOCAL généré par run_inference
    (1, 2, 3... dans l'ordre de détection de CETTE segmentation). Ce n'est
    PAS une référence vers la table Nodule de l'app ctscan — le module
    segmentation est volontairement indépendant de la détection/classification
    et peut tourner sur un scan qui n'a aucun Nodule détecté en base.
    """
    for n in results:
        NoduleSegmentation.objects.update_or_create(
            scan=scan,
            nodule_id_ticnet=n['nodule_id'],
            defaults={
                'rpn_score':          n['rpn_score'],
                'center_mm':          n['center_mm'],
                'center_voxel':       n['center_voxel'],
                'diam_ticnet_mm':     n['diam_ticnet'],
                'diam_seg_mm':        n['diam_seg'],
                'volume_mm3':         n['volume_mm3'],
                'n_voxels':           n['n_voxels'],
                'ct_image_path':      n.get('ct_url', ''),
                'mask_npy_path':      n.get('mask_npy', ''),
                'mask_image_path':    n.get('mask_image', ''),
                'contour_image_path': n.get('contour_url', ''),
                'mesh_json_path':     n.get('mesh_url', '') or '',
            }
        )
        logger.info(f"✓ NoduleSegmentation sauvegardée — scan={scan.id} nodule_local={n['nodule_id']}")


def _build_nodules_response(result):
    """Construit la liste de nodules pour la réponse JSON (URLs relatives → absolues)."""
    nodules_resp = []
    for n in result['nodules']:
        nodules_resp.append({
            'nodule_id':    n['nodule_id'],
            'rpn_score':    n['rpn_score'],
            'center_mm':    n['center_mm'],
            'center_voxel': n['center_voxel'],
            'diam_ticnet':  n['diam_ticnet'],
            'diam_seg':     n['diam_seg'],
            'volume_mm3':   n['volume_mm3'],
            'n_voxels':     n['n_voxels'],
            'ct_url':           _to_url(n.get('ct_url')),
            'mask_image_url':   _to_url(n.get('mask_image')),
            'contour_url':      _to_url(n.get('contour_url')),
            'mesh_url':         _to_url(n.get('mesh_url')),
        })
    return nodules_resp


# ── POST /segment/ — NOUVEAU SCAN (upload ZIP DICOM) ──────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def segment_nodules(request):
    """
    POST /api/segmentation/segment/
    Body (multipart/form-data) :
        dicom_file : ZIP contenant les .dcm
        scan_id    : ID du CtScan en base (obligatoire pour le lien BDD)
    """
    # ── Vérifications ────────────────────────────────────────────────────────
    if 'dicom_file' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': "Champ 'dicom_file' manquant."
        }, status=400)

    scan_id = request.POST.get('scan_id')
    if not scan_id:
        return JsonResponse({
            'success': False,
            'error': "Champ 'scan_id' manquant."
        }, status=400)

    try:
        scan = CtScan.objects.get(pk=scan_id)
    except CtScan.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f"CtScan id={scan_id} introuvable."
        }, status=404)

    # ── Extraction DICOM ─────────────────────────────────────────────────────
    uploaded = request.FILES['dicom_file']
    job_id   = str(uuid.uuid4())[:8]
    job_dir  = MEDIA_ROOT / 'segmentation' / f'job_{job_id}'
    dcm_dir  = job_dir / 'dicom'
    out_dir  = job_dir / 'output'
    dcm_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        zip_path = job_dir / 'upload.zip'
        with open(zip_path, 'wb') as f:
            for chunk in uploaded.chunks():
                f.write(chunk)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.namelist():
                if member.lower().endswith('.dcm'):
                    fname = os.path.basename(member)
                    if not fname:
                        continue
                    with zf.open(member) as src, open(dcm_dir / fname, 'wb') as dst:
                        dst.write(src.read())

    except Exception as e:
        logger.error(f"Erreur extraction ZIP : {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    dcm_files = list(dcm_dir.glob('*.dcm'))
    if len(dcm_files) < 10:
        return JsonResponse({
            'success': False,
            'error': f"Seulement {len(dcm_files)} fichiers .dcm trouvés (min 10)."
        }, status=400)

    # ── Inférence ────────────────────────────────────────────────────────────
    try:
        result = run_inference(
            dicom_dir=str(dcm_dir),
            out_dir=str(out_dir),
            seuil_detection=0.5,
            seuil_segmentation=0.5,
            min_diameter_mm=3.0,
        )
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Erreur inférence : {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # ── Stockage BDD ─────────────────────────────────────────────────────────
    if result['total'] > 0:
        try:
            _save_segmentations(scan, result['nodules'])
        except Exception as e:
            logger.error(f"Erreur sauvegarde BDD : {e}", exc_info=True)
            # non-bloquant : on retourne quand même le résultat

    # ── Réponse JSON ─────────────────────────────────────────────────────────
    return JsonResponse({
        'success': True,
        'job_id':  job_id,
        'scan_id': scan.id,
        'total':   result['total'],
        'duree':   result.get('duree', 0),
        'message': result.get('message', ''),
        'nodules': _build_nodules_response(result),
    }, status=200)


# ── POST /segment-existing/<scan_id>/ — SCAN EXISTANT (.mhd déjà stocké) ─────

@csrf_exempt
@require_http_methods(['POST'])
def segment_existing_scan(request, scan_id):
    """
    POST /api/segmentation/segment-existing/<scan_id>/
    Lance la segmentation à partir du .mhd déjà stocké pour ce scan
    (pas de nouvel upload DICOM). Si le scan n'a pas de .mhd valide,
    retourne une erreur explicite invitant à utiliser /segment/ à la place.
    """
    try:
        scan = CtScan.objects.get(pk=scan_id)
    except CtScan.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f"CtScan id={scan_id} introuvable."
        }, status=404)

    # ── Vérification du fichier .mhd ────────────────────────────────────────
    if not scan.fichier_mhd or not scan.fichier_mhd.name:
        return JsonResponse({
            'success': False,
            'error': (
                "Ce scan n'a pas de fichier .mhd disponible. "
                "Veuillez utiliser l'upload DICOM (nouveau scan) à la place."
            ),
            'fallback_to_upload': True,
        }, status=400)

    mhd_path = Path(scan.fichier_mhd.path)
    if not mhd_path.is_file():
        return JsonResponse({
            'success': False,
            'error': (
                f"Fichier .mhd introuvable sur disque pour ce scan. "
                "Veuillez utiliser l'upload DICOM (nouveau scan) à la place."
            ),
            'fallback_to_upload': True,
        }, status=400)

    if scan.spacing_z is None or scan.spacing_y is None or scan.spacing_x is None:
        return JsonResponse({
            'success': False,
            'error': "Spacing manquant en base pour ce scan, segmentation impossible.",
            'fallback_to_upload': True,
        }, status=400)

    # ── Préparation dossier de sortie ────────────────────────────────────────
    job_id  = str(uuid.uuid4())[:8]
    job_dir = MEDIA_ROOT / 'segmentation' / f'job_{job_id}'
    out_dir = job_dir / 'output'
    out_dir.mkdir(parents=True, exist_ok=True)

    spacing = [scan.spacing_z, scan.spacing_y, scan.spacing_x]

    # ── Inférence ────────────────────────────────────────────────────────────
    try:
        result = run_inference_existing_scan(
            mhd_path=str(mhd_path),
            spacing=spacing,
            out_dir=str(out_dir),
            seuil_detection=0.5,
            seuil_segmentation=0.5,
            min_diameter_mm=3.0,
        )
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Erreur inférence (scan existant) : {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # ── Stockage BDD ─────────────────────────────────────────────────────────
    if result['total'] > 0:
        try:
            _save_segmentations(scan, result['nodules'])
        except Exception as e:
            logger.error(f"Erreur sauvegarde BDD : {e}", exc_info=True)

    # ── Réponse JSON ─────────────────────────────────────────────────────────
    return JsonResponse({
        'success': True,
        'job_id':  job_id,
        'scan_id': scan.id,
        'total':   result['total'],
        'duree':   result.get('duree', 0),
        'message': result.get('message', ''),
        'nodules': _build_nodules_response(result),
    }, status=200)


# ── GET /scan/<scan_id>/ ───────────────────────────────────────────────────────

@require_http_methods(['GET'])
def get_scan_segmentations(request, scan_id):
    """
    GET /api/segmentation/scan/<scan_id>/
    Retourne toutes les segmentations d'un scan depuis la BDD.
    """
    try:
        scan = CtScan.objects.get(pk=scan_id)
    except CtScan.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Scan introuvable.'}, status=404)

    segs = NoduleSegmentation.objects.filter(scan=scan).order_by('nodule_id_ticnet')

    nodules_resp = []
    for s in segs:
        nodules_resp.append({
            'nodule_id_ticnet':  s.nodule_id_ticnet,
            'rpn_score':         s.rpn_score,
            'center_mm':         s.center_mm,
            'center_voxel':      s.center_voxel,
            'diam_ticnet_mm':    s.diam_ticnet_mm,
            'diam_seg_mm':       s.diam_seg_mm,
            'volume_mm3':        s.volume_mm3,
            'n_voxels':          s.n_voxels,
            'ct_url':            _to_url(s.ct_image_path),
            'mask_image_url':    _to_url(s.mask_image_path),
            'contour_url':       _to_url(s.contour_image_path),
            'mesh_url':          _to_url(s.mesh_json_path),
            'created_at':        s.created_at.isoformat(),
        })

    return JsonResponse({
        'success': True,
        'scan_id': scan.id,
        'total':   len(nodules_resp),
        'nodules': nodules_resp,
    })