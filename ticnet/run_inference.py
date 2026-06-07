import sys
sys.path.insert(0, '/home/inas/STicnet')

import os
import numpy as np
import torch

os.environ['CUDA_VISIBLE_DEVICES'] = ''

from config import net_config
from net.main_net import build_model

# ── Paramètres ────────────────────────────────────────────────────────────────
#pid = "1.3.6.1.4.1.14519.5.2.1.6279.6001.100225287222365663678666836860"
# pid = "1.3.6.1.4.1.14519.5.2.1.6279.6001.104562737760173137525888934217"
# data_dir   = "/home/inas/STicnet/preprocessed_test"
pid      = "1.3.6.1.4.1.14519.5.2.1.6279.6001.105495028985881418176186711228"
data_dir = "/home/inas/STicnet/preprocessed_no_mask"
data_dir = "/home/inas/STicnet/preprocessed_no_mask"
checkpoint = "/home/inas/STicnet/results/ticnet/2_fold/model/120.pth"

# ── Charger le modèle ─────────────────────────────────────────────────────────
print("Chargement du modèle...")
model = build_model(net_config)
ckpt = torch.load(checkpoint, map_location='cpu')
model.load_state_dict(ckpt['state_dict'])
model.cpu()
model.use_rcnn = True
model.set_mode('eval')
print("Modèle chargé ✅")

# ── Charger les fichiers preprocessés ────────────────────────────────────────
seg_img = np.load(os.path.join(data_dir, f'{pid}.npy'))
origin  = np.load(os.path.join(data_dir, f'{pid}_origin.npy'))
spacing = np.load(os.path.join(data_dir, f'{pid}_spacing.npy'))
ebox    = np.load(os.path.join(data_dir, f'{pid}_ebox.npy'))

print(f"Shape : {seg_img.shape}")
print(f"Origin : {origin}")
print(f"Spacing : {spacing}")
print(f"Ebox : {ebox}")

# ── Padding multiple de 16 ────────────────────────────────────────────────────
def pad_to_factor(image, factor=16, pad_value=170):
    D, H, W = image.shape
    pad_D = (factor - D % factor) % factor
    pad_H = (factor - H % factor) % factor
    pad_W = (factor - W % factor) % factor
    return np.pad(image, ((0, pad_D), (0, pad_H), (0, pad_W)),
                  mode='constant', constant_values=pad_value)

seg_img = pad_to_factor(seg_img, factor=16, pad_value=170)
print(f"Shape après padding : {seg_img.shape}")

# ── Normalisation exacte BboxReader ──────────────────────────────────────────
seg_img = seg_img[np.newaxis, np.newaxis].astype(np.float32)
seg_img = (seg_img - 128.0) / 128.0
input_tensor = torch.from_numpy(seg_img)

# ── Inference ─────────────────────────────────────────────────────────────────
print("Inference...")
with torch.no_grad():
    model.forward(input_tensor, [], [])

ensembles = model.ensemble_proposals.cpu().numpy()
print(f"Proposals total : {len(ensembles)}")

# ── Filtrer prob > 0.5 ────────────────────────────────────────────────────────
nodules = []
for det in ensembles:
    score = float(det[1])
    if score > 0.5:
        nodules.append({
            "z": float(det[2]),
            "y": float(det[3]),
            "x": float(det[4]),
            "diameter_mm": float(det[5]),
            "probability": score
        })

print(f"\n✅ {len(nodules)} nodules détectés :")
for i, n in enumerate(nodules):
    print(f"  [{i+1}] z={n['z']:.1f}, y={n['y']:.1f}, x={n['x']:.1f}, "
          f"d={n['diameter_mm']:.1f}mm, prob={n['probability']:.4f}")

# ── Conversion voxel preprocessé → coordonnées monde ─────────────────────────
# print(f"\n--- Conversion en coordonnées monde (mm) ---")
# new_spacing = spacing * np.array([194, 512, 512]) / np.array([349, 330, 330])

# for i, n in enumerate(nodules):
#     # voxel preprocessé → voxel resampleé
#     vox_z = n['z'] + ebox[0]
#     vox_y = n['y'] + ebox[1]
#     vox_x = n['x'] + ebox[2]

#     # voxel resampleé → coordonnées monde
#     world_z = origin[0] + vox_z * new_spacing[0]
#     world_y = origin[1] + vox_y * new_spacing[1]
#     world_x = origin[2] + vox_x * new_spacing[2]

#     print(f"  [{i+1}] monde: z={world_z:.1f}, y={world_y:.1f}, x={world_x:.1f}, prob={n['probability']:.4f}")
# ── Conversion voxel preprocessé → coordonnées monde ─────────────────────────
print(f"\n--- Conversion en coordonnées monde (mm) ---")

# new_spacing = spacing car on a resampleé vers 1x1x1mm
# La conversion est : world = origin + (voxel_preprocessé + ebox) * new_spacing
# new_spacing ≈ [1.0, 1.0, 1.0] après resample

for i, n in enumerate(nodules):
    # voxel preprocessé → voxel resampleé (ajouter ebox)
    vox_z = n['z'] + ebox[0]
    vox_y = n['y'] + ebox[1]
    vox_x = n['x'] + ebox[2]

    # voxel resampleé → coordonnées monde
    # new_spacing = 1.0 car on resample vers 1x1x1mm
    world_z = origin[0] + vox_z * 1.0
    world_y = origin[1] + vox_y * 1.0
    world_x = origin[2] + vox_x * 1.0

    print(f"  [{i+1}] monde: z={world_z:.1f}, y={world_y:.1f}, x={world_x:.1f}, prob={n['probability']:.4f}")