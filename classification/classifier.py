"""
classification/classifier.py
----------------------------
Logique d'inférence ResNet50-SWS intégrée dans Django.
Appelé automatiquement après chaque analyse TiCNet réussie (statut=TERMINE).
"""

import logging
import os

import numpy as np
import torch
import SimpleITK as sitk
from monai.networks.nets import resnet50
from monai.transforms import Compose, EnsureChannelFirst, EnsureType, Resize
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Singleton — modèle chargé une seule fois au premier appel
# =============================================================================
_model = None
_device = torch.device("cpu")


def get_model():
    """
    Charge ResNet50-SWS une seule fois (singleton).
    settings.py doit définir :
        CLASSIFICATION_MODEL_PATH = "/chemin/vers/LUNA16_SWS_v11_1_resnet50_SWS.pt"
    """
    global _model
    if _model is not None:
        return _model

    model_path = getattr(settings, "CLASSIFICATION_MODEL_PATH", None)
    if not model_path or not os.path.isfile(model_path):
        raise FileNotFoundError(
            f"Modèle introuvable : {model_path}\n"
            "Ajoute CLASSIFICATION_MODEL_PATH dans settings.py"
        )

    logger.info(f"[Classifier] Chargement modèle : {model_path}")
    model = resnet50(
        pretrained=False,
        spatial_dims=3,
        n_input_channels=1,
        num_classes=2,
    )
    ckpt = torch.load(model_path, map_location=_device)
    if isinstance(ckpt, dict) and "state_dict" in ckpt:
        ckpt = ckpt["state_dict"]
    ckpt = {k.replace("module.", ""): v for k, v in ckpt.items()}
    model.load_state_dict(ckpt, strict=True)
    model.to(_device)
    model.eval()

    n = sum(p.numel() for p in model.parameters())
    logger.info(f"[Classifier] ✅ Modèle chargé — {n:,} paramètres")
    _model = model
    return _model


# =============================================================================
# Chargement volume .mhd
# =============================================================================
def load_mhd(mhd_path: str):
    """Charge un .mhd et retourne volume (Z,Y,X) en HU brutes."""
    image  = sitk.ReadImage(mhd_path)
    volume = sitk.GetArrayFromImage(image).astype(np.float32)
    return volume


# =============================================================================
# Extraction patch depuis coordonnées voxel (déjà fournies par TiCNet)
# =============================================================================
def extract_patch(volume, voxel_x, voxel_y, voxel_z, patch_size=64):
    """
    Extrait un cube patch_size³ centré sur (voxel_x, voxel_y, voxel_z).
    volume est indexé (Z, Y, X) par SimpleITK → GetArrayFromImage.
    """
    cx, cy, cz = int(round(voxel_x)), int(round(voxel_y)), int(round(voxel_z))
    half = patch_size // 2
    Z, Y, X = volume.shape

    z0, z1 = cz - half, cz + half
    y0, y1 = cy - half, cy + half
    x0, x1 = cx - half, cx + half

    if z0 < 0 or z1 > Z or y0 < 0 or y1 > Y or x0 < 0 or x1 > X:
        patch = np.zeros((patch_size, patch_size, patch_size), dtype=np.float32)
        vz0, vz1 = max(0, z0), min(Z, z1)
        vy0, vy1 = max(0, y0), min(Y, y1)
        vx0, vx1 = max(0, x0), min(X, x1)
        patch[vz0-z0:vz0-z0+(vz1-vz0),
              vy0-y0:vy0-y0+(vy1-vy0),
              vx0-x0:vx0-x0+(vx1-vx0)] = volume[vz0:vz1, vy0:vy1, vx0:vx1]
    else:
        patch = volume[z0:z1, y0:y1, x0:x1].copy()

    return patch


def preprocess_patch(patch, patch_size=64):
    """
    Normalise HU → [0,1] (identique au preprocessing PiNS d'entraînement)
    puis prépare le tensor pour le modèle.
    """
    patch = np.clip(patch, -1000, 400)
    patch = (patch - (-1000)) / (400 - (-1000))

    transforms = Compose([
        EnsureChannelFirst(channel_dim="no_channel"),
        Resize(spatial_size=(patch_size, patch_size, patch_size),
               mode="trilinear", align_corners=True),
        EnsureType(dtype=torch.float32),
    ])
    tensor = transforms(patch).unsqueeze(0)  # (1,1,64,64,64)
    return tensor


# =============================================================================
# Prédiction
# =============================================================================
def predict(tensor):
    """Retourne label (0=Benigne/1=Maligne), proba_maligne, proba_benigne."""
    model = get_model()
    with torch.no_grad():
        logits = model(tensor.to(_device))
        probas = torch.softmax(logits, dim=1)[0]
        label  = int(probas.argmax().item())
    return {
        "label":         label,
        "proba_maligne": round(float(probas[1].item()), 4),
        "proba_benigne": round(float(probas[0].item()), 4),
    }


# =============================================================================
# Fonction principale — classifie tous les nodules d'un CtScan
# =============================================================================
def classify_scan(ctscan_instance):
    """
    Classifie tous les nodules d'un CtScan et sauvegarde en base.

    Args:
        ctscan_instance : instance de ctscan.models.CtScan
                          (utilise .fichier_mhd.path et .nodules.all())

    Returns:
        list[NoduleClassification] : objets créés/mis à jour
    """
    from classification.models import NoduleClassification

    mhd_path = ctscan_instance.fichier_mhd.path
    nodules  = ctscan_instance.nodules.all()  # related_name="nodules" sur Nodule.ctscan

    if not nodules.exists():
        logger.warning(f"[Classifier] CtScan {ctscan_instance.id} — aucun nodule.")
        return []

    logger.info(f"[Classifier] CtScan {ctscan_instance.id} — "
                f"{nodules.count()} nodule(s) à classifier")

    volume  = load_mhd(mhd_path)
    results = []

    for nod in nodules:
        try:
            patch  = extract_patch(volume, nod.voxel_x, nod.voxel_y, nod.voxel_z)
            tensor = preprocess_patch(patch)
            pred   = predict(tensor)

            obj, created = NoduleClassification.objects.update_or_create(
                scan=ctscan_instance,
                nodule_id_ticnet=nod.id,
                defaults={
                    "rang":           nod.rang,
                    "voxel_x":        nod.voxel_x,
                    "voxel_y":        nod.voxel_y,
                    "voxel_z":        nod.voxel_z,
                    "diametre_mm":    nod.diametre_mm,
                    "prob_detection": nod.probabilite,
                    "label":          pred["label"],
                    "proba_maligne":  pred["proba_maligne"],
                    "proba_benigne":  pred["proba_benigne"],
                }
            )
            results.append(obj)
            action = "créé" if created else "mis à jour"
            logger.info(
                f"  Nodule #{nod.rang} → "
                f"{'Maligne' if pred['label']==1 else 'Benigne'} "
                f"(p={pred['proba_maligne']:.4f}) [{action}]"
            )

        except Exception as e:
            logger.error(f"  ❌ Nodule #{nod.rang} échec : {e}")

    return results