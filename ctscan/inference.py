"""
inference.py — Preprocessing + Inference TiCNet intégrés dans Django
Importe directement depuis ticnet/ (package intégré au backend)
Chargement du modèle UNE SEULE FOIS via CtScanConfig.ready()
"""
import os
import sys
import time
import shutil
import logging
import tempfile

import numpy as np
import torch
from skimage import measure

os.environ['CUDA_VISIBLE_DEVICES'] = ''  # forcer CPU

logger = logging.getLogger(__name__)

# ── Chemin checkpoint ─────────────────────────────────────────────────────────
CHECKPOINT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'ticnet', 'results', 'ticnet', '1_fold', 'model', '114.pth'
)

# ── Singleton modèle ──────────────────────────────────────────────────────────
_model = None


def get_model():
    """
    Charge le modèle TiCNet une seule fois et le garde en mémoire.
    Appelé par CtScanConfig.ready() au démarrage Django.
    """
    global _model
    if _model is not None:
        return _model

    logger.info("[TiCNet] Chargement du modèle...")
    t = time.time()

    # Import direct depuis le package ticnet intégré — aucun sys.path hack
    from ticnet.ticnet_config import net_config
    from ticnet.net.main_net import build_model

    model = build_model(net_config)
    checkpoint = torch.load(CHECKPOINT_PATH, map_location='cpu')
    model.load_state_dict(checkpoint['state_dict'])
    model.cpu()
    model.use_rcnn = True
    model.set_mode('eval')

    _model = model
    logger.info(f"[TiCNet] Modèle chargé en {time.time()-t:.1f}s ")
    return _model


# ── Helpers preprocessing ─────────────────────────────────────────────────────
def _pad_to_factor(image, factor=16, pad_value=170):
    D, H, W = image.shape
    pad_D = (factor - D % factor) % factor
    pad_H = (factor - H % factor) % factor
    pad_W = (factor - W % factor) % factor
    return np.pad(image, ((0, pad_D), (0, pad_H), (0, pad_W)),
                  mode='constant', constant_values=pad_value)


# ── Preprocessing ─────────────────────────────────────────────────────────────
def preprocess(mhd_path):
    """
    Preprocessing complet sans masque pulmonaire externe.

    Args:
        mhd_path (str): chemin vers le fichier .mhd
                        (le .raw doit être dans le même dossier)
    Returns:
        seg_img (np.ndarray): volume preprocessé (D, H, W) uint8
        origin  (np.ndarray): origine ITK [z, y, x] en mm
        spacing (np.ndarray): spacing original [z, y, x] en mm
        ebox    (np.ndarray): offset crop [z_min, y_min, x_min]
    """
    from ticnet.utils.preprocess import (
        load_itk_image, HU2uint8, binarize, exclude_corner_middle,
        volume_filter, exclude_air, fill_hole, apply_mask, resample,
        get_lung_box
    )

    logger.info("[Preprocessing] Chargement image...")
    img, origin, spacing = load_itk_image(mhd_path)
    logger.info(f"  Shape originale : {img.shape}, spacing : {spacing}")

    logger.info("[Preprocessing] Segmentation poumons...")
    binary_mask = binarize(img, spacing)
    label = measure.label(binary_mask, connectivity=1)
    label = exclude_corner_middle(label)
    label = volume_filter(label, spacing)
    binary_mask, has_lung = exclude_air(label, spacing)
    binary_mask = fill_hole(binary_mask)

    if not has_lung:
        logger.warning("[Preprocessing]  Poumons non détectés — masque complet utilisé")
        binary_mask1 = np.ones(img.shape, dtype=bool)
        binary_mask2 = np.zeros(img.shape, dtype=bool)
    else:
        logger.info("[Preprocessing]  Poumons détectés")
        label = measure.label(binary_mask, connectivity=1)
        props = sorted(measure.regionprops(label),
                       key=lambda x: x.area, reverse=True)
        binary_mask1 = label == props[0].label
        binary_mask2 = (label == props[1].label
                        if len(props) > 1
                        else np.zeros_like(binary_mask1))

    img     = HU2uint8(img)
    seg_img = apply_mask(img, binary_mask1, binary_mask2)

    logger.info("[Preprocessing] Resampling (order=3)...")
    seg_img, _ = resample(seg_img, spacing, order=3)
    logger.info(f"  Shape après resample : {seg_img.shape}")

    lung_box = get_lung_box(binary_mask, seg_img.shape)
    z_min, z_max = lung_box[0]
    y_min, y_max = lung_box[1]
    x_min, x_max = lung_box[2]
    seg_img = seg_img[z_min:z_max, y_min:y_max, x_min:x_max]
    logger.info(f"  Shape après crop : {seg_img.shape}")

    ebox = np.array([z_min, y_min, x_min])
    return seg_img, origin, spacing, ebox


# ── Inference ─────────────────────────────────────────────────────────────────
def run_inference(seg_img, origin, ebox, seuil_prob=0.90):
    """
    Lance l'inference TiCNet et retourne la liste des nodules détectés.

    Returns:
        list[dict]: nodules triés par probabilité décroissante
    """
    model = get_model()

    seg_padded = _pad_to_factor(seg_img, factor=16, pad_value=170)
    logger.info(f"[Inference] Shape après padding : {seg_padded.shape}")

    seg_padded   = seg_padded[np.newaxis, np.newaxis].astype(np.float32)
    seg_padded   = (seg_padded - 128.0) / 128.0
    input_tensor = torch.from_numpy(seg_padded)

    logger.info("[Inference] TiCNet CPU...")
    t = time.time()
    with torch.no_grad():
        model.forward(input_tensor, [], [])
    logger.info(f"[Inference] Terminée en {time.time()-t:.1f}s")

    ensembles = model.ensemble_proposals.cpu().numpy()
    logger.info(f"[Inference] {len(ensembles)} proposals totales")

    nodules_bruts = []
    for det in ensembles:
        score = float(det[1])
        if score > seuil_prob:
            vox_z = float(det[2])
            vox_y = float(det[3])
            vox_x = float(det[4])

            world_z = origin[0] + (vox_z + ebox[0]) * 1.0
            world_y = origin[1] + (vox_y + ebox[1]) * 1.0
            world_x = origin[2] + (vox_x + ebox[2]) * 1.0

            nodules_bruts.append({
                "voxel": {"z": vox_z, "y": vox_y, "x": vox_x},
                "monde": {
                    "z": round(world_z, 2),
                    "y": round(world_y, 2),
                    "x": round(world_x, 2),
                },
                "diametre_mm": round(float(det[5]), 2),
                "probabilite": round(score, 4),
            })

    nodules_bruts.sort(key=lambda n: n["probabilite"], reverse=True)
    for i, n in enumerate(nodules_bruts, start=1):
        n["rang"] = i

    logger.info(f"[Inference] {len(nodules_bruts)} nodules (prob > {seuil_prob})")
    return nodules_bruts


# ── Fonction principale appelée par views.py ──────────────────────────────────
def analyser_ctscan(mhd_path, raw_path):
    """
    Pipeline complet : preprocessing → inference.
    mhd_path et raw_path doivent être dans le MÊME dossier.

    Returns:
        dict {
          "nodules": list[dict],
          "origin":  [z, y, x],
          "spacing": [z, y, x],
          "ebox":    [z, y, x],
          "duree":   float (secondes)
        }
    """
    t0      = time.time()
    tmp_dir = tempfile.mkdtemp(prefix='ctscan_')

    try:
        # Copier .mhd et .raw dans le même répertoire temporaire
        mhd_dest = os.path.join(tmp_dir, os.path.basename(mhd_path))
        raw_dest = os.path.join(tmp_dir, os.path.basename(raw_path))
        shutil.copy2(mhd_path, mhd_dest)
        shutil.copy2(raw_path, raw_dest)

        seg_img, origin, spacing, ebox = preprocess(mhd_dest)
        nodules = run_inference(seg_img, origin, ebox)

        return {
            "nodules": nodules,
            "origin":  origin.tolist(),
            "spacing": spacing.tolist(),
            "ebox":    ebox.tolist(),
            "duree":   round(time.time() - t0, 1),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)