# """
# inference.py — Pipeline DICOM → TiCNet → Segmentation pour Django (Pulmo-X)
# """

# import os
# import sys
# import json
# import time
# import logging
# import numpy as np
# import torch
# import scipy.ndimage as ndimage
# import matplotlib
# matplotlib.use('Agg')
# import matplotlib.pyplot as plt
# from pathlib import Path
# import pydicom

# from django.conf import settings as django_settings

# logger = logging.getLogger(__name__)

# # ── PATCH CPU FORCÉ ──────────────────────────────────────────────────────────
# torch.cuda.is_available = lambda: False

# _original_cuda = torch.Tensor.cuda
# def _patched_cuda(self, *args, **kwargs):
#     return self.cpu()
# torch.Tensor.cuda = _patched_cuda

# _original_to = torch.Tensor.to
# def _patched_to(self, *args, **kwargs):
#     new_args = []
#     for a in args:
#         if isinstance(a, str) and 'cuda' in a:
#             new_args.append('cpu')
#         elif isinstance(a, torch.device) and a.type == 'cuda':
#             new_args.append(torch.device('cpu'))
#         else:
#             new_args.append(a)
#     return _original_to(self, *new_args, **kwargs)
# torch.Tensor.to = _patched_to

# class _CudaTensorProxy:
#     def __init__(self, base_type):
#         self._base = base_type
#     def __call__(self, *args, **kwargs):
#         kwargs.pop('device', None)
#         return self._base(*args, **kwargs)

# torch.cuda.FloatTensor = _CudaTensorProxy(torch.FloatTensor)
# torch.cuda.LongTensor  = _CudaTensorProxy(torch.LongTensor)
# torch.cuda.ByteTensor  = _CudaTensorProxy(torch.ByteTensor)
# torch.cuda.IntTensor   = _CudaTensorProxy(torch.IntTensor)
   
# # ── Chemins ──────────────────────────────────────────────────────────────────
# TICNET_CKPT = Path(django_settings.TICNET_MODEL_PATH)
# SEG_CKPT    = Path(django_settings.SEGMENTATION_MODEL_PATH)

# if not TICNET_CKPT.exists():
#     raise FileNotFoundError(f"Checkpoint TiCNet non trouvé : {TICNET_CKPT}")
# if not SEG_CKPT.exists():
#     raise FileNotFoundError(f"Checkpoint segmentation non trouvé : {SEG_CKPT}")

# # ── Singleton modèle ─────────────────────────────────────────────────────────
# _model  = None
# _device = None

# def get_model():
#     global _model, _device
#     if _model is not None:
#         return _model, _device

#     logger.info("[Modèle] Chargement...")
#     t = time.time()

#     # net/ et config.py sont dans segmentation/
#     seg_dir = str(Path(__file__).resolve().parent.parent)
#     if seg_dir not in sys.path:
#         sys.path.insert(0, seg_dir)

#     from net.main_net import MainNet
#     from net.config import net_config as config


#     device = torch.device('cpu')
#     model  = MainNet(config, mode='eval').to(device)

#     ckpt = torch.load(TICNET_CKPT, map_location=device, weights_only=False)
#     model.load_state_dict(ckpt['state_dict'], strict=False)

#     seg = torch.load(SEG_CKPT, map_location=device, weights_only=False)
#     model.seg_head.load_state_dict(seg['seg_head_state'])

#     model.use_rcnn = True
#     model.set_mode('eval')

#     _model  = model
#     _device = device
#     logger.info(f"[Modèle] Chargé en {time.time()-t:.1f}s sur CPU")
#     return _model, _device


# # ── ÉTAPE 1 — Chargement DICOM ───────────────────────────────────────────────

# def load_dicom(dicom_dir):
#     slices = []
#     for f in Path(dicom_dir).rglob('*.dcm'):
#         try:
#             ds = pydicom.dcmread(str(f), force=True)
#             if getattr(ds, 'Modality', '') != 'CT': continue
#             if not hasattr(ds, 'ImagePositionPatient'): continue
#             if len(ds.pixel_array.shape) != 2: continue
#             slices.append(ds)
#         except Exception:
#             continue

#     if len(slices) < 10:
#         raise ValueError(f"Pas assez de slices CT ({len(slices)} trouvées, min 10).")

#     slices.sort(key=lambda s: float(s.ImagePositionPatient[2]))

#     image = np.stack([s.pixel_array for s in slices]).astype(np.int16)
#     for i, s in enumerate(slices):
#         intercept = float(getattr(s, 'RescaleIntercept', -1024))
#         slope     = float(getattr(s, 'RescaleSlope', 1))
#         if slope != 1:
#             image[i] = (slope * image[i].astype(np.float64)).astype(np.int16)
#         image[i] += np.int16(intercept)

#     ps      = slices[0].PixelSpacing
#     dz      = abs(float(slices[1].ImagePositionPatient[2]) - float(slices[0].ImagePositionPatient[2]))
#     spacing = np.array([dz, float(ps[0]), float(ps[1])])

#     logger.info(f"[DICOM] {len(slices)} slices, shape={image.shape}")
#     return image, spacing


# def resample_volume(image, spacing, new_spacing=(1.0, 1.0, 1.0)):
#     resize_factor    = spacing / np.array(new_spacing)
#     new_shape        = np.round(image.shape * resize_factor).astype(int)
#     real_resize      = new_shape / image.shape
#     image_resampled  = ndimage.zoom(image, real_resize, order=1)
#     return image_resampled, (spacing / real_resize)


# # ── ÉTAPE 2 — Détection TiCNet ───────────────────────────────────────────────

# def hu_to_ticnet_format(vol_hu):
#     vol = np.clip(vol_hu, -1200.0, 600.0).astype(np.float32)
#     vol = (vol - (-1200.0)) / (600.0 - (-1200.0)) * 255.0
#     vol = np.clip(vol, 0, 255).astype(np.float32)
#     vol = (vol - 128.0) / 128.0
#     return vol


# def pad_to_factor(image, factor=16, pad_value=0.0):
#     D, H, W = image.shape
#     pad_D = (factor - D % factor) % factor
#     pad_H = (factor - H % factor) % factor
#     pad_W = (factor - W % factor) % factor
#     return np.pad(image, ((0, pad_D), (0, pad_H), (0, pad_W)),
#                   mode='constant', constant_values=pad_value)


# def detect_with_ticnet(model, vol_ticnet, device, seuil=0.5):
#     vol_padded   = pad_to_factor(vol_ticnet, factor=16, pad_value=0.0)
#     input_tensor = torch.from_numpy(
#         vol_padded[np.newaxis, np.newaxis].astype(np.float32)
#     ).to(device)

#     logger.info(f"[Détection] TiCNet forward shape={vol_padded.shape}")
#     t = time.time()

#     with torch.no_grad():
#         model(input_tensor, [], [])
#         ensembles = model.ensemble_proposals.cpu().numpy()

#     logger.info(f"[Détection] Terminée en {time.time()-t:.1f}s")

#     candidates = []
#     for det in ensembles:
#         score = float(det[1])
#         if score > seuil:
#             z_mm, y_mm, x_mm     = float(det[2]), float(det[3]), float(det[4])
#             d_mm, h_mm, w_mm     = float(det[5]), float(det[6]), float(det[7])
#             diameter_mm          = (d_mm + h_mm + w_mm) / 3.0
#             candidates.append({
#                 'center_mm':   [z_mm, y_mm, x_mm],
#                 'diameter_mm': round(diameter_mm, 2),
#                 'prob':        round(score, 4),
#             })

#     candidates.sort(key=lambda c: c['prob'], reverse=True)
#     logger.info(f"[Détection] {len(candidates)} candidats (score > {seuil})")
#     return candidates


# # ── ÉTAPE 3 — Segmentation ───────────────────────────────────────────────────

# def mm_to_voxel(center_mm, spacing=(1.0, 1.0, 1.0)):
#     return [
#         int(round(center_mm[0] / spacing[0])),
#         int(round(center_mm[1] / spacing[1])),
#         int(round(center_mm[2] / spacing[2])),
#     ]


# def extract_crop_for_seghead(vol_hu_resampled, center_voxel_zyx, S=64):
#     cz, cy, cx = center_voxel_zyx
#     D, H, W    = vol_hu_resampled.shape

#     z0 = max(0, cz - S//2); z1 = min(D, z0 + S)
#     y0 = max(0, cy - S//2); y1 = min(H, y0 + S)
#     x0 = max(0, cx - S//2); x1 = min(W, x0 + S)
#     z0 = max(0, z1 - S); y0 = max(0, y1 - S); x0 = max(0, x1 - S)

#     crop = vol_hu_resampled[z0:z1, y0:y1, x0:x1].copy().astype(np.float32)

#     if crop.shape != (S, S, S):
#         pad  = [(0, S - s) for s in crop.shape]
#         crop = np.pad(crop, pad, mode='constant', constant_values=-1000)

#     min_hu, max_hu = -1000.0, 400.0
#     crop = np.clip(crop, min_hu, max_hu)
#     crop = (crop - min_hu) / (max_hu - min_hu)
#     return crop.astype(np.float32)


# def segment_with_attenunet(model, device, crop_np, threshold=0.5):
#     x = torch.from_numpy(crop_np[None, None]).float().to(device)
#     with torch.no_grad():
#         features, feat_4    = model.feature_net(x)
#         pred, _             = model.seg_head(feat_4, features)
#         probs               = torch.sigmoid(pred).cpu().numpy()[0, 0]
#         mask                = (probs > threshold).astype(np.uint8)
#     return mask, probs


# def compute_metrics(mask, spacing=(1.0, 1.0, 1.0)):
#     n_voxels = int(mask.sum())
#     vol_mm3  = float(n_voxels) * float(np.prod(spacing))
#     if n_voxels > 0:
#         diam       = round(2 * ((3 * vol_mm3) / (4 * np.pi)) ** (1/3), 2)
#         center_zyx = [round(float(c), 1) for c in np.argwhere(mask).mean(axis=0)]
#     else:
#         diam       = 0.0
#         center_zyx = [32.0, 32.0, 32.0]
#     return {'n_voxels': n_voxels, 'volume_mm3': round(vol_mm3, 2),
#             'diameter_mm': diam, 'center_zyx': center_zyx}


# # ── Génération images ─────────────────────────────────────────────────────────

# def generate_ct_crop(crop, nodule_id, out_dir):
#     cz  = crop.shape[0] // 2
#     fig, ax = plt.subplots(1, 1, figsize=(4, 4), facecolor='black')
#     ax.imshow(crop[cz], cmap='gray', vmin=0, vmax=1)
#     ax.axis('off')
#     ax.set_title('CT crop', color='white', fontsize=10)
#     plt.tight_layout()
#     path = os.path.join(out_dir, f'nodule_{nodule_id:03d}_ct.png')
#     plt.savefig(path, dpi=120, bbox_inches='tight', facecolor='black')
#     plt.close()
#     return path


# def generate_mask_only(mask, nodule_id, out_dir):
#     cz  = mask.shape[0] // 2
#     fig, ax = plt.subplots(1, 1, figsize=(4, 4), facecolor='black')
#     ax.imshow(mask[cz], cmap='gray')
#     ax.axis('off')
#     ax.set_title('Masque', color='white', fontsize=10)
#     plt.tight_layout()
#     path = os.path.join(out_dir, f'nodule_{nodule_id:03d}_mask.png')
#     plt.savefig(path, dpi=120, bbox_inches='tight', facecolor='black')
#     plt.close()
#     return path


# def generate_ct_with_contour(crop, mask, nodule_id, out_dir):
#     cz  = crop.shape[0] // 2
#     fig, ax = plt.subplots(1, 1, figsize=(4, 4), facecolor='black')
#     ax.imshow(crop[cz], cmap='gray', vmin=0, vmax=1)
#     if mask[cz].sum() > 0:
#         ax.contour(mask[cz], colors='lime', linewidths=2)
#     ax.axis('off')
#     ax.set_title('CT + contour', color='white', fontsize=10)
#     plt.tight_layout()
#     path = os.path.join(out_dir, f'nodule_{nodule_id:03d}_contour.png')
#     plt.savefig(path, dpi=120, bbox_inches='tight', facecolor='black')
#     plt.close()
#     return path


# # ── Génération mesh 3D ────────────────────────────────────────────────────────

# def generate_3d_mesh(mask, nodule_id, out_dir, spacing=(1.0, 1.0, 1.0)):
#     try:
#         from skimage import measure

#         if mask.sum() < 10:
#             return None

#         mask_smooth = ndimage.gaussian_filter(mask.astype(float), sigma=1.5)
#         mask_smooth = (mask_smooth > 0.3).astype(np.uint8)

#         labeled, nlabels = ndimage.label(mask_smooth)
#         if nlabels == 0:
#             return None

#         labels_counts         = np.bincount(labeled.flatten())
#         labels_counts[0]      = 0
#         largest_label         = labels_counts.argmax()
#         mask_cleaned          = (labeled == largest_label).astype(np.uint8)

#         if mask_cleaned.sum() < 10:
#             return None

#         spacing_tuple = tuple(float(s) for s in spacing)

#         try:
#             verts, faces, normals, values = measure.marching_cubes(
#                 mask_cleaned.astype(np.float32),
#                 level=0.5,
#                 spacing=spacing_tuple,
#                 allow_degenerate=False
#             )
#         except Exception as e:
#             logger.error(f"Erreur marching cubes : {e}")
#             return None

#         if len(verts) < 4 or len(faces) < 4:
#             return None

#         center         = verts.mean(axis=0)
#         verts_centered = verts - center
#         bbox_min       = verts_centered.min(axis=0)
#         bbox_max       = verts_centered.max(axis=0)

#         mesh_data = {
#             'vertices':       verts_centered.tolist(),
#             'faces':          faces.tolist(),
#             'normals':        normals.tolist(),
#             'center':         center.tolist(),
#             'nodule_id':      int(nodule_id),
#             'volume_mm3':     float(mask_cleaned.sum() * np.prod(spacing_tuple)),
#             'n_vertices':     int(len(verts)),
#             'n_faces':        int(len(faces)),
#             'bounds':         {'min': bbox_min.tolist(), 'max': bbox_max.tolist()},
#             'original_shape': [int(s) for s in mask.shape],
#             'spacing':        list(spacing_tuple),
#         }

#         mesh_path = os.path.join(out_dir, f'nodule_{nodule_id:03d}_mesh.json')
#         with open(mesh_path, 'w') as f:
#             json.dump(mesh_data, f)

#         logger.info(f"✓ Mesh 3D : {len(verts)} vertices, {len(faces)} faces")
#         return mesh_path

#     except Exception as e:
#         logger.error(f"Erreur mesh 3D : {e}", exc_info=True)
#         return None


# # ── Pipeline principal ────────────────────────────────────────────────────────

# def run_inference(dicom_dir, out_dir,
#                   seuil_detection=0.5,
#                   seuil_segmentation=0.5,
#                   min_diameter_mm=3.0):
#     t0 = time.time()
#     os.makedirs(out_dir, exist_ok=True)
#     model, device = get_model()

#     vol_hu, spacing         = load_dicom(dicom_dir)
#     vol_hu_res, new_spacing = resample_volume(vol_hu, spacing)
#     vol_ticnet              = hu_to_ticnet_format(vol_hu_res)
#     candidates              = detect_with_ticnet(model, vol_ticnet, device, seuil_detection)

#     # Filtrage >= 90%
#     candidates = [c for c in candidates if c['prob'] >= 0.9]
#     logger.info(f"[Pipeline] {len(candidates)} candidats après filtrage >= 90%")

#     if not candidates:
#         return {
#             'total': 0, 'nodules': [],
#             'duree': round(time.time() - t0, 1),
#             'message': 'Aucun nodule avec score >= 90% détecté'
#         }

#     results   = []
#     nodule_id = 0

#     for cand in candidates:
#         center_mm    = cand['center_mm']
#         prob_score   = cand['prob']
#         center_voxel = mm_to_voxel(center_mm, new_spacing)
#         logger.info(f"[Crop] center_mm={center_mm}")
#         logger.info(f"[Crop] new_spacing={new_spacing}")
#         logger.info(f"[Crop] center_voxel={center_voxel}")
#         logger.info(f"[Crop] vol_hu_res.shape={vol_hu_res.shape}")
#         crop         = extract_crop_for_seghead(vol_hu_res, center_voxel, S=64)
#         mask, probs  = segment_with_attenunet(model, device, crop, seuil_segmentation)
#         logger.info(f"[SegHead] probs min={probs.min():.4f} max={probs.max():.4f} mean={probs.mean():.4f}")
#         logger.info(f"[SegHead] voxels > 0.5 : {(probs > 0.5).sum()}")
#         logger.info(f"[SegHead] voxels > 0.3 : {(probs > 0.3).sum()}")
#         logger.info(f"[SegHead] voxels > 0.1 : {(probs > 0.1).sum()}")
#         metrics      = compute_metrics(mask, new_spacing)

#         if metrics['diameter_mm'] < min_diameter_mm:
#             continue

#         nodule_id += 1

#         # Sauvegarder masque et crop numpy
#         np.save(os.path.join(out_dir, f'nodule_{nodule_id:03d}_mask.npy'), mask)
#         np.save(os.path.join(out_dir, f'nodule_{nodule_id:03d}_image.npy'), crop)

#         # Générer les 3 images + mesh
#         ct_path      = generate_ct_crop(crop, nodule_id, out_dir)
#         mask_path    = generate_mask_only(mask, nodule_id, out_dir)
#         contour_path = generate_ct_with_contour(crop, mask, nodule_id, out_dir)
#         mesh_path    = generate_3d_mesh(mask, nodule_id, out_dir, new_spacing)

#         results.append({
#             'nodule_id':    nodule_id,
#             'rpn_score':    prob_score,
#             'center_mm':    center_mm,
#             'center_voxel': center_voxel,
#             'diam_ticnet':  cand['diameter_mm'],
#             'diam_seg':     metrics['diameter_mm'],
#             'volume_mm3':   metrics['volume_mm3'],
#             'n_voxels':     metrics['n_voxels'],
#             'ct_url':       ct_path,
#             'mask_npy':     os.path.join(out_dir, f'nodule_{nodule_id:03d}_mask.npy'),
#             'mask_image':   mask_path,
#             'contour_url':  contour_path,
#             'mesh_url':     mesh_path,
#         })

#         logger.info(f"✓ Nodule {nodule_id} : diam={metrics['diameter_mm']:.1f}mm "
#                     f"vol={metrics['volume_mm3']:.1f}mm³ score={prob_score:.3f}")

#     duree = round(time.time() - t0, 1)
#     logger.info(f"[Pipeline] Terminé — {nodule_id} nodules en {duree}s")
#     return {'total': nodule_id, 'nodules': results, 'duree': duree}
"""
inference.py — Pipeline DICOM → TiCNet → Segmentation pour Django (Pulmo-X)

Deux points d'entrée :
  - run_inference(...)              : nouveau scan, upload ZIP DICOM
  - run_inference_existing_scan(...) : scan déjà existant, .mhd/.raw déjà stocké
Les deux partagent le même pipeline interne (_run_pipeline) — seule la
façon de charger le volume initial diffère.
"""

import os
import sys
import json
import time
import logging
import numpy as np
import torch
import scipy.ndimage as ndimage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import pydicom
import SimpleITK as sitk

from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

# ── PATCH CPU FORCÉ ──────────────────────────────────────────────────────────
torch.cuda.is_available = lambda: False

_original_cuda = torch.Tensor.cuda
def _patched_cuda(self, *args, **kwargs):
    return self.cpu()
torch.Tensor.cuda = _patched_cuda

_original_to = torch.Tensor.to
def _patched_to(self, *args, **kwargs):
    new_args = []
    for a in args:
        if isinstance(a, str) and 'cuda' in a:
            new_args.append('cpu')
        elif isinstance(a, torch.device) and a.type == 'cuda':
            new_args.append(torch.device('cpu'))
        else:
            new_args.append(a)
    return _original_to(self, *new_args, **kwargs)
torch.Tensor.to = _patched_to

class _CudaTensorProxy:
    def __init__(self, base_type):
        self._base = base_type
    def __call__(self, *args, **kwargs):
        kwargs.pop('device', None)
        return self._base(*args, **kwargs)

torch.cuda.FloatTensor = _CudaTensorProxy(torch.FloatTensor)
torch.cuda.LongTensor  = _CudaTensorProxy(torch.LongTensor)
torch.cuda.ByteTensor  = _CudaTensorProxy(torch.ByteTensor)
torch.cuda.IntTensor   = _CudaTensorProxy(torch.IntTensor)

# ── Chemins ──────────────────────────────────────────────────────────────────
TICNET_CKPT = Path(django_settings.TICNET_MODEL_PATH)
SEG_CKPT    = Path(django_settings.SEGMENTATION_MODEL_PATH)

if not TICNET_CKPT.exists():
    raise FileNotFoundError(f"Checkpoint TiCNet non trouvé : {TICNET_CKPT}")
if not SEG_CKPT.exists():
    raise FileNotFoundError(f"Checkpoint segmentation non trouvé : {SEG_CKPT}")

# ── Singleton modèle ─────────────────────────────────────────────────────────
_model  = None
_device = None

def get_model():
    global _model, _device
    if _model is not None:
        return _model, _device

    logger.info("[Modèle] Chargement...")
    t = time.time()

    # net/ et config.py sont dans segmentation/
    seg_dir = str(Path(__file__).resolve().parent.parent)
    if seg_dir not in sys.path:
        sys.path.insert(0, seg_dir)

    from net.main_net import MainNet
    from net.config import net_config as config

    device = torch.device('cpu')
    model  = MainNet(config, mode='eval').to(device)

    ckpt = torch.load(TICNET_CKPT, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['state_dict'], strict=False)

    seg = torch.load(SEG_CKPT, map_location=device, weights_only=False)
    model.seg_head.load_state_dict(seg['seg_head_state'])

    model.use_rcnn = True
    model.set_mode('eval')

    _model  = model
    _device = device
    logger.info(f"[Modèle] Chargé en {time.time()-t:.1f}s sur CPU")
    return _model, _device


# ── ÉTAPE 1 — Chargement du volume ───────────────────────────────────────────

def load_dicom(dicom_dir):
    """
    Charge un volume CT depuis un dossier de fichiers .dcm (nouveau scan).
    Retourne le volume en HU + le spacing déduit des métadonnées DICOM.
    """
    slices = []
    for f in Path(dicom_dir).rglob('*.dcm'):
        try:
            ds = pydicom.dcmread(str(f), force=True)
            if getattr(ds, 'Modality', '') != 'CT': continue
            if not hasattr(ds, 'ImagePositionPatient'): continue
            if len(ds.pixel_array.shape) != 2: continue
            slices.append(ds)
        except Exception:
            continue

    if len(slices) < 10:
        raise ValueError(f"Pas assez de slices CT ({len(slices)} trouvées, min 10).")

    slices.sort(key=lambda s: float(s.ImagePositionPatient[2]))

    image = np.stack([s.pixel_array for s in slices]).astype(np.int16)
    for i, s in enumerate(slices):
        intercept = float(getattr(s, 'RescaleIntercept', -1024))
        slope     = float(getattr(s, 'RescaleSlope', 1))
        if slope != 1:
            image[i] = (slope * image[i].astype(np.float64)).astype(np.int16)
        image[i] += np.int16(intercept)

    ps      = slices[0].PixelSpacing
    dz      = abs(float(slices[1].ImagePositionPatient[2]) - float(slices[0].ImagePositionPatient[2]))
    spacing = np.array([dz, float(ps[0]), float(ps[1])])

    logger.info(f"[DICOM] {len(slices)} slices, shape={image.shape}")
    return image, spacing


def load_mhd(mhd_path):
    """
    Charge un volume CT depuis un fichier .mhd déjà existant (scan existant).
    Le .mhd doit être en HU brut (c'est le cas pour les fichiers sauvegardés
    par l'app ctscan via _save_scan_files — aucune conversion HU->uint8 n'y
    est appliquée).

    Ne retourne QUE le volume : le spacing est volontairement laissé à la
    charge de l'appelant (views.py), qui doit le fournir depuis les champs
    CtScan.spacing_z/y/x déjà validés en base. SimpleITK.GetSpacing() est en
    ordre (x, y, z) — le redéduire ici serait une source classique d'inversion
    d'axes, déjà rencontrée dans ce projet.

    Args:
        mhd_path (str): chemin vers le fichier .mhd (le .raw doit être
                        dans le même dossier).
    Returns:
        vol_hu (np.ndarray): volume (D, H, W) en unités Hounsfield, int16
    """
    image  = sitk.ReadImage(str(mhd_path))
    vol_hu = sitk.GetArrayFromImage(image).astype(np.int16)
    logger.info(f"[MHD] Chargé depuis {mhd_path}, shape={vol_hu.shape}")
    return vol_hu


def resample_volume(image, spacing, new_spacing=(1.0, 1.0, 1.0)):
    resize_factor    = spacing / np.array(new_spacing)
    new_shape        = np.round(image.shape * resize_factor).astype(int)
    real_resize      = new_shape / image.shape
    image_resampled  = ndimage.zoom(image, real_resize, order=1)
    return image_resampled, (spacing / real_resize)


# ── ÉTAPE 2 — Détection TiCNet ───────────────────────────────────────────────

def hu_to_ticnet_format(vol_hu):
    vol = np.clip(vol_hu, -1200.0, 600.0).astype(np.float32)
    vol = (vol - (-1200.0)) / (600.0 - (-1200.0)) * 255.0
    vol = np.clip(vol, 0, 255).astype(np.float32)
    vol = (vol - 128.0) / 128.0
    return vol


def pad_to_factor(image, factor=16, pad_value=0.0):
    D, H, W = image.shape
    pad_D = (factor - D % factor) % factor
    pad_H = (factor - H % factor) % factor
    pad_W = (factor - W % factor) % factor
    return np.pad(image, ((0, pad_D), (0, pad_H), (0, pad_W)),
                  mode='constant', constant_values=pad_value)


def detect_with_ticnet(model, vol_ticnet, device, seuil=0.5):
    vol_padded   = pad_to_factor(vol_ticnet, factor=16, pad_value=0.0)
    input_tensor = torch.from_numpy(
        vol_padded[np.newaxis, np.newaxis].astype(np.float32)
    ).to(device)

    logger.info(f"[Détection] TiCNet forward shape={vol_padded.shape}")
    t = time.time()

    with torch.no_grad():
        model(input_tensor, [], [])
        ensembles = model.ensemble_proposals.cpu().numpy()

    logger.info(f"[Détection] Terminée en {time.time()-t:.1f}s")

    candidates = []
    for det in ensembles:
        score = float(det[1])
        if score > seuil:
            z_mm, y_mm, x_mm     = float(det[2]), float(det[3]), float(det[4])
            d_mm, h_mm, w_mm     = float(det[5]), float(det[6]), float(det[7])
            diameter_mm          = (d_mm + h_mm + w_mm) / 3.0
            candidates.append({
                'center_mm':   [z_mm, y_mm, x_mm],
                'diameter_mm': round(diameter_mm, 2),
                'prob':        round(score, 4),
            })

    candidates.sort(key=lambda c: c['prob'], reverse=True)
    logger.info(f"[Détection] {len(candidates)} candidats (score > {seuil})")
    return candidates


# ── ÉTAPE 3 — Segmentation ───────────────────────────────────────────────────

def mm_to_voxel(center_mm, spacing=(1.0, 1.0, 1.0)):
    return [
        int(round(center_mm[0] / spacing[0])),
        int(round(center_mm[1] / spacing[1])),
        int(round(center_mm[2] / spacing[2])),
    ]


def extract_crop_for_seghead(vol_hu_resampled, center_voxel_zyx, S=64):
    cz, cy, cx = center_voxel_zyx
    D, H, W    = vol_hu_resampled.shape

    z0 = max(0, cz - S//2); z1 = min(D, z0 + S)
    y0 = max(0, cy - S//2); y1 = min(H, y0 + S)
    x0 = max(0, cx - S//2); x1 = min(W, x0 + S)
    z0 = max(0, z1 - S); y0 = max(0, y1 - S); x0 = max(0, x1 - S)

    crop = vol_hu_resampled[z0:z1, y0:y1, x0:x1].copy().astype(np.float32)

    if crop.shape != (S, S, S):
        pad  = [(0, S - s) for s in crop.shape]
        crop = np.pad(crop, pad, mode='constant', constant_values=-1000)

    min_hu, max_hu = -1000.0, 400.0
    crop = np.clip(crop, min_hu, max_hu)
    crop = (crop - min_hu) / (max_hu - min_hu)
    return crop.astype(np.float32)


def segment_with_attenunet(model, device, crop_np, threshold=0.5):
    x = torch.from_numpy(crop_np[None, None]).float().to(device)
    with torch.no_grad():
        features, feat_4    = model.feature_net(x)
        pred, _             = model.seg_head(feat_4, features)
        probs               = torch.sigmoid(pred).cpu().numpy()[0, 0]
        mask                = (probs > threshold).astype(np.uint8)
    return mask, probs


def compute_metrics(mask, spacing=(1.0, 1.0, 1.0)):
    n_voxels = int(mask.sum())
    vol_mm3  = float(n_voxels) * float(np.prod(spacing))
    if n_voxels > 0:
        diam       = round(2 * ((3 * vol_mm3) / (4 * np.pi)) ** (1/3), 2)
        center_zyx = [round(float(c), 1) for c in np.argwhere(mask).mean(axis=0)]
    else:
        diam       = 0.0
        center_zyx = [32.0, 32.0, 32.0]
    return {'n_voxels': n_voxels, 'volume_mm3': round(vol_mm3, 2),
            'diameter_mm': diam, 'center_zyx': center_zyx}


# ── Génération images ─────────────────────────────────────────────────────────

def generate_ct_crop(crop, nodule_id, out_dir):
    cz  = crop.shape[0] // 2
    fig, ax = plt.subplots(1, 1, figsize=(4, 4), facecolor='black')
    ax.imshow(crop[cz], cmap='gray', vmin=0, vmax=1)
    ax.axis('off')
    ax.set_title('CT crop', color='white', fontsize=10)
    plt.tight_layout()
    path = os.path.join(out_dir, f'nodule_{nodule_id:03d}_ct.png')
    plt.savefig(path, dpi=120, bbox_inches='tight', facecolor='black')
    plt.close()
    return path


def generate_mask_only(mask, nodule_id, out_dir):
    cz  = mask.shape[0] // 2
    fig, ax = plt.subplots(1, 1, figsize=(4, 4), facecolor='black')
    ax.imshow(mask[cz], cmap='gray')
    ax.axis('off')
    ax.set_title('Masque', color='white', fontsize=10)
    plt.tight_layout()
    path = os.path.join(out_dir, f'nodule_{nodule_id:03d}_mask.png')
    plt.savefig(path, dpi=120, bbox_inches='tight', facecolor='black')
    plt.close()
    return path


def generate_ct_with_contour(crop, mask, nodule_id, out_dir):
    cz  = crop.shape[0] // 2
    fig, ax = plt.subplots(1, 1, figsize=(4, 4), facecolor='black')
    ax.imshow(crop[cz], cmap='gray', vmin=0, vmax=1)
    if mask[cz].sum() > 0:
        ax.contour(mask[cz], colors='lime', linewidths=2)
    ax.axis('off')
    ax.set_title('CT + contour', color='white', fontsize=10)
    plt.tight_layout()
    path = os.path.join(out_dir, f'nodule_{nodule_id:03d}_contour.png')
    plt.savefig(path, dpi=120, bbox_inches='tight', facecolor='black')
    plt.close()
    return path


# ── Génération mesh 3D ────────────────────────────────────────────────────────

def generate_3d_mesh(mask, nodule_id, out_dir, spacing=(1.0, 1.0, 1.0)):
    try:
        from skimage import measure

        if mask.sum() < 10:
            return None

        mask_smooth = ndimage.gaussian_filter(mask.astype(float), sigma=1.5)
        mask_smooth = (mask_smooth > 0.3).astype(np.uint8)

        labeled, nlabels = ndimage.label(mask_smooth)
        if nlabels == 0:
            return None

        labels_counts         = np.bincount(labeled.flatten())
        labels_counts[0]      = 0
        largest_label         = labels_counts.argmax()
        mask_cleaned          = (labeled == largest_label).astype(np.uint8)

        if mask_cleaned.sum() < 10:
            return None

        spacing_tuple = tuple(float(s) for s in spacing)

        try:
            verts, faces, normals, values = measure.marching_cubes(
                mask_cleaned.astype(np.float32),
                level=0.5,
                spacing=spacing_tuple,
                allow_degenerate=False
            )
        except Exception as e:
            logger.error(f"Erreur marching cubes : {e}")
            return None

        if len(verts) < 4 or len(faces) < 4:
            return None

        center         = verts.mean(axis=0)
        verts_centered = verts - center
        bbox_min       = verts_centered.min(axis=0)
        bbox_max       = verts_centered.max(axis=0)

        mesh_data = {
            'vertices':       verts_centered.tolist(),
            'faces':          faces.tolist(),
            'normals':        normals.tolist(),
            'center':         center.tolist(),
            'nodule_id':      int(nodule_id),
            'volume_mm3':     float(mask_cleaned.sum() * np.prod(spacing_tuple)),
            'n_vertices':     int(len(verts)),
            'n_faces':        int(len(faces)),
            'bounds':         {'min': bbox_min.tolist(), 'max': bbox_max.tolist()},
            'original_shape': [int(s) for s in mask.shape],
            'spacing':        list(spacing_tuple),
        }

        mesh_path = os.path.join(out_dir, f'nodule_{nodule_id:03d}_mesh.json')
        with open(mesh_path, 'w') as f:
            json.dump(mesh_data, f)

        logger.info(f"✓ Mesh 3D : {len(verts)} vertices, {len(faces)} faces")
        return mesh_path

    except Exception as e:
        logger.error(f"Erreur mesh 3D : {e}", exc_info=True)
        return None


# ── Pipeline interne commun (privé — utilisé par les deux points d'entrée) ───

def _run_pipeline(vol_hu, spacing, out_dir, t0,
                   seuil_detection=0.5,
                   seuil_segmentation=0.5,
                   min_diameter_mm=3.0):
    """
    Pipeline partagé : resampling → détection TiCNet → segmentation par
    nodule → génération images/mesh → métriques.

    Ne dépend pas de la façon dont vol_hu/spacing ont été obtenus
    (DICOM ou .mhd) — c'est strictement le même traitement dans les deux cas.
    """
    model, device = get_model()

    vol_hu_res, new_spacing = resample_volume(vol_hu, spacing)
    vol_ticnet               = hu_to_ticnet_format(vol_hu_res)
    candidates                = detect_with_ticnet(model, vol_ticnet, device, seuil_detection)

    # Filtrage >= 90%
    candidates = [c for c in candidates if c['prob'] >= 0.9]
    logger.info(f"[Pipeline] {len(candidates)} candidats après filtrage >= 90%")

    if not candidates:
        return {
            'total': 0, 'nodules': [],
            'duree': round(time.time() - t0, 1),
            'message': 'Aucun nodule avec score >= 90% détecté'
        }

    results   = []
    nodule_id = 0

    for cand in candidates:
        center_mm    = cand['center_mm']
        prob_score   = cand['prob']
        center_voxel = mm_to_voxel(center_mm, new_spacing)
        logger.info(f"[Crop] center_mm={center_mm}")
        logger.info(f"[Crop] new_spacing={new_spacing}")
        logger.info(f"[Crop] center_voxel={center_voxel}")
        logger.info(f"[Crop] vol_hu_res.shape={vol_hu_res.shape}")
        crop         = extract_crop_for_seghead(vol_hu_res, center_voxel, S=64)
        mask, probs  = segment_with_attenunet(model, device, crop, seuil_segmentation)
        logger.info(f"[SegHead] probs min={probs.min():.4f} max={probs.max():.4f} mean={probs.mean():.4f}")
        logger.info(f"[SegHead] voxels > 0.5 : {(probs > 0.5).sum()}")
        logger.info(f"[SegHead] voxels > 0.3 : {(probs > 0.3).sum()}")
        logger.info(f"[SegHead] voxels > 0.1 : {(probs > 0.1).sum()}")
        metrics      = compute_metrics(mask, new_spacing)

        if metrics['diameter_mm'] < min_diameter_mm:
            continue

        nodule_id += 1

        # Sauvegarder masque et crop numpy
        np.save(os.path.join(out_dir, f'nodule_{nodule_id:03d}_mask.npy'), mask)
        np.save(os.path.join(out_dir, f'nodule_{nodule_id:03d}_image.npy'), crop)

        # Générer les 3 images + mesh
        ct_path      = generate_ct_crop(crop, nodule_id, out_dir)
        mask_path    = generate_mask_only(mask, nodule_id, out_dir)
        contour_path = generate_ct_with_contour(crop, mask, nodule_id, out_dir)
        mesh_path    = generate_3d_mesh(mask, nodule_id, out_dir, new_spacing)

        results.append({
            'nodule_id':    nodule_id,
            'rpn_score':    prob_score,
            'center_mm':    center_mm,
            'center_voxel': center_voxel,
            'diam_ticnet':  cand['diameter_mm'],
            'diam_seg':     metrics['diameter_mm'],
            'volume_mm3':   metrics['volume_mm3'],
            'n_voxels':     metrics['n_voxels'],
            'ct_url':       ct_path,
            'mask_npy':     os.path.join(out_dir, f'nodule_{nodule_id:03d}_mask.npy'),
            'mask_image':   mask_path,
            'contour_url':  contour_path,
            'mesh_url':     mesh_path,
        })

        logger.info(f"✓ Nodule {nodule_id} : diam={metrics['diameter_mm']:.1f}mm "
                    f"vol={metrics['volume_mm3']:.1f}mm³ score={prob_score:.3f}")

    duree = round(time.time() - t0, 1)
    logger.info(f"[Pipeline] Terminé — {nodule_id} nodules en {duree}s")
    return {'total': nodule_id, 'nodules': results, 'duree': duree}


# ── Point d'entrée 1 — NOUVEAU SCAN (upload ZIP DICOM) ────────────────────────

def run_inference(dicom_dir, out_dir,
                   seuil_detection=0.5,
                   seuil_segmentation=0.5,
                   min_diameter_mm=3.0):
    """
    Cas "nouveau scan" : le médecin upload un ZIP DICOM, on segmente direct.
    Signature strictement identique à l'originale — aucun changement requis
    côté views.py pour ce cas.
    """
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)

    vol_hu, spacing = load_dicom(dicom_dir)

    return _run_pipeline(
        vol_hu, spacing, out_dir, t0,
        seuil_detection=seuil_detection,
        seuil_segmentation=seuil_segmentation,
        min_diameter_mm=min_diameter_mm,
    )


# ── Point d'entrée 2 — SCAN EXISTANT (.mhd/.raw déjà stocké) ──────────────────

def run_inference_existing_scan(mhd_path, spacing, out_dir,
                                 seuil_detection=0.5,
                                 seuil_segmentation=0.5,
                                 min_diameter_mm=3.0):
    """
    Cas "scan existant" : le .mhd/.raw a déjà été produit et stocké par
    l'app ctscan lors de l'analyse initiale (CtScan.fichier_mhd). On ne
    redemande pas le ZIP DICOM au médecin.

    Args:
        mhd_path (str): chemin absolu vers le fichier .mhd existant.
        spacing  (list|tuple|np.ndarray): [spacing_z, spacing_y, spacing_x]
                 en mm — à fournir depuis CtScan.spacing_z/y/x en base de
                 données par l'appelant (views.py), PAS redéduit du fichier.
        out_dir  (str): dossier de sortie pour les images/mesh générés.
    """
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)

    vol_hu      = load_mhd(mhd_path)
    spacing_arr = np.array(spacing, dtype=np.float64)

    return _run_pipeline(
        vol_hu, spacing_arr, out_dir, t0,
        seuil_detection=seuil_detection,
        seuil_segmentation=seuil_segmentation,
        min_diameter_mm=min_diameter_mm,
    )