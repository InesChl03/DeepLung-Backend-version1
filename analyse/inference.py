# """
# TiCNet Inference Engine — adapté Windows CPU pour Django
# """

# import os
# import sys
# import warnings
# import numpy as np
# import torch
# import nrrd
# import SimpleITK as sitk
# import matplotlib
# matplotlib.use('Agg')  # pas de display GUI — nécessaire pour Django
# import matplotlib.pyplot as plt
# import matplotlib.patches as patches

# warnings.filterwarnings("ignore")

# # ── Ajoute le dossier TiCNet au path Python ──────────────────────────────────
# TICNET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'TiCNet')
# if TICNET_DIR not in sys.path:
#     sys.path.insert(0, TICNET_DIR)

# from net.main_net import build_model
# import numpy as np
# # Force CPU — désactive complètement CUDA avant tout import TiCNet
# import os
# os.environ['CUDA_VISIBLE_DEVICES'] = ''  # ← cache tous les GPUs

# import torch
# # Monkey-patch pour forcer CPU partout dans TiCNet
# original_cuda = torch.Tensor.cuda
# def cpu_only(self, *args, **kwargs):
#     return self.cpu()
# torch.Tensor.cuda = cpu_only

# original_module_cuda = torch.nn.Module.cuda
# def module_cpu_only(self, *args, **kwargs):
#     return self.cpu()
# torch.nn.Module.cuda = module_cpu_only
# # ── Config réseau (copie de config.py TiCNet) ────────────────────────────────

# def get_anchors(bases, aspect_ratios):
#     anchors = []
#     for b in bases:
#         for asp in aspect_ratios:
#             d, h, w = b * asp[0], b * asp[1], b * asp[2]
#             anchors.append([d, h, w])
#     return anchors


# NET_CONFIG = {
#     'anchors': get_anchors([5, 10, 20, 30, 50], [[1, 1, 1]]),
#     'roi_names': ['nodule'],
#     'pad_value': 170,
#     'crop_size': [128, 128, 128],
#     'bbox_border': 8,
#     'stride': 4,
#     'max_stride': 16,
#     'num_neg': 800,
#     'th_neg': 0.02,
#     'th_pos_train': 0.5,
#     'th_pos_val': 1,
#     'num_hard': 3,
#     'bound_size': 12,
#     'blacklist': [],
#     'num_class': 2,
#     'aux_loss': False,
#     'augtype': {'flip': True, 'rotate': True, 'scale': True, 'swap': False},
#     'r_rand_crop': 0.,
#     'rpn_train_bg_thresh_high': 0.02,
#     'rpn_train_fg_thresh_low': 0.5,
#     'rpn_train_nms_num': 300,
#     'rpn_train_nms_pre_score_threshold': 0.5,
#     'rpn_train_nms_overlap_threshold': 0.1,
#     'rpn_test_nms_pre_score_threshold': 0.5,
#     'rpn_test_nms_overlap_threshold': 0.1,
#     'rcnn_crop_size': (7, 7, 7),
#     'rcnn_train_fg_thresh_low': 0.5,
#     'rcnn_train_bg_thresh_high': 0.1,
#     'rcnn_train_batch_size': 64,
#     'rcnn_train_fg_fraction': 0.5,
#     'rcnn_train_nms_pre_score_threshold': 0.5,
#     'rcnn_train_nms_overlap_threshold': 0.1,
#     'rcnn_test_nms_pre_score_threshold': 0.0,
#     'rcnn_test_nms_overlap_threshold': 0.1,
#     'box_reg_weight': [1., 1., 1., 1., 1., 1.],
#     'hidden_dim': 64,
#     'dropout': 0.1,
#     'nheads': 8,
#     'dim_feedforward': 256,
#     'enc_layers': 6,
#     'dec_layers': 6,
#     'pre_norm': '',
#     'return_intermediate_dec': True,
#     'position_embedding': 'sine',
#     'num_queries': 512,
# }


# # ── Chargement du modèle (singleton) ─────────────────────────────────────────

# _model = None


# _model = None

# def load_model(pth_path: str):
#     global _model
#     _model = None  # ← force rechargement à chaque fois (temporaire pour debug)

#     print(f"[TiCNet] Loading model from {pth_path} on CPU...")
#     _model = build_model(NET_CONFIG)
#     _model = _model.cpu()

#     checkpoint = torch.load(pth_path, map_location=torch.device('cpu'))
#     _model.load_state_dict(checkpoint['state_dict'])
#     _model.eval()

#     # ── DEBUG architecture ──────────────────────────────
#     total_params = sum(p.numel() for p in _model.parameters())
#     print(f"[TiCNet] Nombre de paramètres : {total_params:,}")
#     print(f"[TiCNet] Epoch du checkpoint   : {checkpoint.get('epoch', 'N/A')}")
#     # ────────────────────────────────────────────────────

#     print("[TiCNet] Model loaded.")
#     return _model


# def read_ct_file(filepath: str) -> np.ndarray:
#     ext = os.path.splitext(filepath)[1].lower()

#     if ext == '.npy':
#         arr = np.load(filepath).astype(np.float32)
#         print(f"[TiCNet] Fichier .npy lu : shape={arr.shape}")
#         print(f"[TiCNet] Min={arr.min()}, Max={arr.max()}")
#         return arr  # ← retourne brut, normalisation dans preprocess

#     elif ext == '.nrrd':
#         arr, _ = nrrd.read(filepath)
#         arr = arr.astype(np.float32)
#         print(f"[TiCNet] Fichier .nrrd lu : shape={arr.shape}")
#         return arr  # ← retourne brut, normalisation dans preprocess

#     elif ext == '.zip':
#         arr, spacing = _read_dicom_zip(filepath)
#         arr = _resample_to_1mm(arr, spacing)
#         # Convertit HU → uint8 exactement comme HU2uint8 dans preprocess.py
#         arr = np.clip(arr, -1200, 600)
#         arr = (arr - (-1200)) / (600 - (-1200))
#         arr = (arr * 255).astype(np.float32)
#         return arr

#     elif ext in ['.mhd', '.nii', '.nii.gz']:
#         itk_img = sitk.ReadImage(filepath)
#         arr = sitk.GetArrayFromImage(itk_img).astype(np.float32)
#         spacing = list(reversed(itk_img.GetSpacing()))
#         arr = _resample_to_1mm(arr, spacing)
#         arr = np.clip(arr, -1200, 600)
#         arr = (arr - (-1200)) / (600 - (-1200))
#         arr = (arr * 255).astype(np.float32)
#         return arr

#     elif ext == '.dcm':
#         itk_img = sitk.ReadImage(filepath)
#         arr = sitk.GetArrayFromImage(itk_img).astype(np.float32)
#         spacing = list(reversed(itk_img.GetSpacing()))
#         arr = _resample_to_1mm(arr, spacing)
#         arr = np.clip(arr, -1200, 600)
#         arr = (arr - (-1200)) / (600 - (-1200))
#         arr = (arr * 255).astype(np.float32)
#         return arr

#     elif ext in ['.png', '.jpg', '.jpeg']:
#         from PIL import Image
#         img = Image.open(filepath).convert('L')
#         arr = np.array(img, dtype=np.float32)
#         arr = arr[np.newaxis, ...]
#         return arr

#     else:
#         raise ValueError(f"Format non supporté : {ext}")


# def preprocess_for_inference(arr: np.ndarray) -> torch.Tensor:
#     from scipy.ndimage import zoom
#     import math

#     # pad2factor — exactement comme BboxReader.eval
#     def pad2factor(image, factor=16, pad_value=0):
#         depth, height, width = image.shape
#         d = int(math.ceil(depth / float(factor))) * factor
#         h = int(math.ceil(height / float(factor))) * factor
#         w = int(math.ceil(width / float(factor))) * factor
#         pad = [[0, d - depth], [0, h - height], [0, w - width]]
#         return np.pad(image, pad, 'constant', constant_values=pad_value)

#     # Prend le volume 3D
#     volume = arr if arr.ndim == 3 else arr[0]

#     # pad2factor comme BboxReader
#     volume = pad2factor(volume, factor=16, pad_value=170)

#     # Normalisation exacte de BboxReader : (x - 128) / 128
#     volume = (volume.astype(np.float32) - 128.) / 128.

#     print(f"[TiCNet] After pad2factor shape : {volume.shape}")
#     print(f"[TiCNet] After normalization min={volume.min():.3f}, max={volume.max():.3f}")

#     # Ajoute dimensions batch et canal
#     tensor = torch.from_numpy(volume).float()
#     tensor = tensor.unsqueeze(0).unsqueeze(0)
#     return tensor
# def _read_dicom_zip(zip_filepath: str):
#     """Retourne (array, spacing)"""
#     import tempfile, zipfile

#     with tempfile.TemporaryDirectory() as tmpdir:
#         with zipfile.ZipFile(zip_filepath, 'r') as zf:
#             zf.extractall(tmpdir)

#         dcm_files = []
#         for root, dirs, files in os.walk(tmpdir):
#             for f in files:
#                 if f.lower().endswith('.dcm') or _is_dicom(os.path.join(root, f)):
#                     dcm_files.append(os.path.join(root, f))

#         if not dcm_files:
#             raise ValueError("Aucun fichier DICOM trouvé dans le ZIP.")

#         print(f"[TiCNet] {len(dcm_files)} fichiers DICOM trouvés.")
#         dicom_dir = os.path.dirname(dcm_files[0])

#         reader    = sitk.ImageSeriesReader()
#         series_ids = reader.GetGDCMSeriesIDs(dicom_dir)

#         if not series_ids:
#             raise ValueError("Aucune série DICOM valide trouvée.")

#         dicom_series = reader.GetGDCMSeriesFileNames(dicom_dir, series_ids[0])
#         reader.SetFileNames(dicom_series)
#         itk_img = reader.Execute()

#         arr     = sitk.GetArrayFromImage(itk_img).astype(np.float32)
#         spacing = list(reversed(itk_img.GetSpacing()))  # → [Z_spacing, Y_spacing, X_spacing]

#         print(f"[TiCNet] Volume DICOM lu : shape={arr.shape}, spacing={spacing}")
#         return arr, spacing


# def _resample_to_1mm(arr: np.ndarray, spacing: list) -> np.ndarray:
#     """
#     Resample le volume pour que chaque voxel = 1mm.
#     C'est exactement ce que fait preprocess.py de LUNA16.
#     """
#     from scipy.ndimage import zoom

#     spacing = np.array(spacing, dtype=np.float32)
#     new_shape = np.round(arr.shape * spacing).astype(int)
#     scale     = new_shape / np.array(arr.shape)

#     print(f"[TiCNet] Resample : {arr.shape} → {tuple(new_shape)} (spacing={spacing})")
#     arr_resampled = zoom(arr, scale, order=1)
#     return arr_resampled


# def apply_nms(detections: list, threshold: float = 0.1) -> list:
#     # ← vérifie taille avant tout
#     if not detections or len(detections) == 0:
#         return []

#     pd = np.array(detections, dtype=np.float32)

#     # ← vérifie que l'array n'est pas vide
#     if pd.size == 0 or pd.ndim < 2 or pd.shape[0] == 0:
#         return []

#     x1 = pd[:, 0] - pd[:, 3]
#     y1 = pd[:, 1] - pd[:, 3]
#     z1 = pd[:, 2] - pd[:, 3]
#     x2 = pd[:, 0] + pd[:, 3]
#     y2 = pd[:, 1] + pd[:, 3]
#     z2 = pd[:, 2] + pd[:, 3]
#     scores = pd[:, 4]
#     order  = scores.argsort()[::-1]
#     areas  = (x2 - x1 + 1) * (y2 - y1 + 1) * (z2 - z1 + 1)
#     keep   = []

#     while order.size > 0:
#         i = order[0]
#         keep.append(i)
#         if order.size == 1:
#             break
#         xx1 = np.maximum(x1[i], x1[order[1:]])
#         yy1 = np.maximum(y1[i], y1[order[1:]])
#         zz1 = np.maximum(z1[i], z1[order[1:]])
#         xx2 = np.minimum(x2[i], x2[order[1:]])
#         yy2 = np.minimum(y2[i], y2[order[1:]])
#         zz2 = np.minimum(z2[i], z2[order[1:]])
#         inter = (np.maximum(0., xx2 - xx1 + 1) *
#                  np.maximum(0., yy2 - yy1 + 1) *
#                  np.maximum(0., zz2 - zz1 + 1))
#         iou   = inter / (areas[i] + areas[order[1:]] - inter)
#         inds  = np.where(iou <= threshold)[0]
#         order = order[inds + 1]

#     return pd[keep].tolist()



    



# def run_inference(pth_path: str, ct_filepath: str, output_dir: str):
#     import numpy as np
#     os.makedirs(output_dir, exist_ok=True)

#     # 1. Charge modèle
#     model = load_model(pth_path)

#     # 2. Lit CT
#     arr = read_ct_file(ct_filepath)

#     # ── DEBUG ──────────────────────────────────────────
#     print(f"[DEBUG] Shape du volume    : {arr.shape}")
#     print(f"[DEBUG] Min valeur         : {arr.min():.4f}")
#     print(f"[DEBUG] Max valeur         : {arr.max():.4f}")
#     print(f"[DEBUG] Moyenne            : {arr.mean():.4f}")
#     # ───────────────────────────────────────────────────

#     # 3. Préprocessing
#     tensor = preprocess_for_inference(arr)

#     # ── DEBUG ──────────────────────────────────────────
#     print(f"[DEBUG] Shape tensor       : {tensor.shape}")
#     # ───────────────────────────────────────────────────

#     # 4. Inférence CPU
#     model.use_rcnn = True
#     model.set_mode('eval')

#     with torch.no_grad():
#         truth_bboxes = np.array([[]])
#         truth_labels = np.array([[]])
#         model.forward(tensor, truth_bboxes, truth_labels)

#     # ── DEBUG scores bruts RPN ──────────────────────────
#     rpn_logits = model.rpn_logits_flat.detach().numpy()
#     rpn_scores = 1 / (1 + np.exp(-rpn_logits))  # sigmoid
#     print(f"[DEBUG] RPN logits shape    : {rpn_logits.shape}")
#     print(f"[DEBUG] RPN scores max      : {rpn_scores.max():.4f}")
#     print(f"[DEBUG] RPN scores mean     : {rpn_scores.mean():.4f}")
#     print(f"[DEBUG] RPN scores > 0.1    : {(rpn_scores > 0.1).sum()}")
#     print(f"[DEBUG] RPN scores > 0.05   : {(rpn_scores > 0.05).sum()}")
#     print(f"[DEBUG] RPN scores > 0.01   : {(rpn_scores > 0.01).sum()}")
#     # ────────────────────────────────────────────────────

#     # 5. Récupère les résultats
#     ensembles = model.ensemble_proposals.detach().numpy()

#     # ── DEBUG ──────────────────────────────────────────
#     print(f"[DEBUG] Ensemble shape     : {ensembles.shape}")
#     print(f"[DEBUG] Ensemble proposals : {ensembles[:5]}")
#     print(f"[DEBUG] RPN proposals      : {len(model.rpn_proposals)}")
#     if len(ensembles) > 0:
#         print(f"[DEBUG] Probabilités max   : {ensembles[:, 1].max():.4f}")
#         print(f"[DEBUG] Probabilités min   : {ensembles[:, 1].min():.4f}")
#         print(f"[DEBUG] > 0.5             : {(ensembles[:, 1] > 0.5).sum()}")
#         print(f"[DEBUG] > 0.3             : {(ensembles[:, 1] > 0.3).sum()}")
#         print(f"[DEBUG] > 0.1             : {(ensembles[:, 1] > 0.1).sum()}")
#     # ───────────────────────────────────────────────────

#     # 6. Filtre par seuil de probabilité
#     detections = []
#     for det in ensembles:
#         if det[1] > 0.5:
#             detections.append([
#                 float(det[4]),  # coordX
#                 float(det[3]),  # coordY
#                 float(det[2]),  # coordZ
#                 float(det[5]),  # diameter_mm
#                 float(det[1]),  # probability
#             ])

#     # ── DEBUG ──────────────────────────────────────────
#     print(f"[DEBUG] Détections > 0.5   : {len(detections)}")
#     # ───────────────────────────────────────────────────

#     # 7. NMS
#     detections = apply_nms(detections, threshold=0.1)

#     # 8. Génère visualisations
#     slices_dir = os.path.join(output_dir, 'slices')
#     _generate_visualizations(arr, detections, slices_dir)

#     # 9. Résultats structurés
#     nodules = []
#     for det in detections:
#         nodules.append({
#             'coordX':      round(det[0], 2),
#             'coordY':      round(det[1], 2),
#             'coordZ':      round(det[2], 2),
#             'diameter_mm': round(det[3], 2),
#             'probability': round(det[4], 4),
#             'risk':        _get_risk_level(det[4]),
#         })

#     return {
#         'nodule_count':    len(nodules),
#         'nodules':         nodules,
#         'max_probability': max([n['probability'] for n in nodules], default=0.0),
#         'slices_dir':      slices_dir,
#     }
# # ── Visualisation ─────────────────────────────────────────────────────────────

# def _generate_visualizations(arr: np.ndarray, detections: list, slices_dir: str):
#     """
#     Génère les slices PNG avec les boîtes de détection dessinées.
#     Sauvegarde uniquement les slices qui contiennent des détections.
#     """
#     os.makedirs(slices_dir, exist_ok=True)

#     # Normalise pour l'affichage
#     volume = arr if arr.ndim == 3 else arr[0]
#     volume = np.clip(volume, 0, 1)

#     if not detections:
#         # Pas de détection — sauvegarde slice du milieu
#         mid = volume.shape[0] // 2
#         _save_slice(volume[mid], mid, [], slices_dir)
#         return

#     # Trouve les slices concernées par les détections
#     affected_slices = set()
#     for det in detections:
#         z, d = det[2], det[3]
#         start = max(0, int(z - d / 2))
#         end   = min(volume.shape[0] - 1, int(z + d / 2))
#         for s in range(start, end + 1):
#             affected_slices.add(s)

#     for i in affected_slices:
#         slice_dets = []
#         for det in detections:
#             z, d = det[2], det[3]
#             if int(z - d / 2) <= i <= int(z + d / 2):
#                 slice_dets.append(det)
#         _save_slice(volume[i], i, slice_dets, slices_dir)


# def _save_slice(slice_arr: np.ndarray, idx: int, detections: list, out_dir: str):
#     fig, ax = plt.subplots(1, figsize=(6, 6))
#     ax.imshow(slice_arr, cmap='bone')
#     ax.set_xticks([])
#     ax.set_yticks([])
#     ax.axis('off')

#     for det in detections:
#         x, y, d, prob = det[0], det[1], det[3], det[4]
#         rect = patches.Rectangle(
#             (x - d / 2, y - d / 2), d, d,
#             linewidth=2, edgecolor='white', facecolor='none'
#         )
#         ax.add_patch(rect)
#         ax.text(
#             x - d / 2, y - d / 2 - 2,
#             f'{prob:.2f}',
#             color='white', fontsize=7,
#             bbox=dict(facecolor='black', alpha=0.4, pad=1)
#         )

#     plt.tight_layout(pad=0)
#     plt.savefig(os.path.join(out_dir, f'slice_{idx:04d}.png'), dpi=100, bbox_inches='tight')
#     plt.close()


# def _get_risk_level(probability: float) -> str:
#     if probability >= 0.85:
#         return "CRITIQUE"
#     elif probability >= 0.70:
#         return "ELEVE"
#     elif probability >= 0.50:
#         return "MODERE"
#     else:
#         return "FAIBLE"
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    




























"""
TiCNet Inference Engine — adapté Windows CPU pour Django
"""

import os
import sys
import warnings
import numpy as np
import torch
import nrrd
import SimpleITK as sitk
import matplotlib
matplotlib.use('Agg')  # pas de display GUI — nécessaire pour Django
import matplotlib.pyplot as plt
import matplotlib.patches as patches

warnings.filterwarnings("ignore")

# ── Ajoute le dossier TiCNet au path Python ──────────────────────────────────
TICNET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'TiCNet')
if TICNET_DIR not in sys.path:
    sys.path.insert(0, TICNET_DIR)

from net.main_net import build_model
import numpy as np
# Force CPU — désactive complètement CUDA avant tout import TiCNet
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # ← cache tous les GPUs

import torch
# Monkey-patch pour forcer CPU partout dans TiCNet
original_cuda = torch.Tensor.cuda
def cpu_only(self, *args, **kwargs):
    return self.cpu()
torch.Tensor.cuda = cpu_only

original_module_cuda = torch.nn.Module.cuda
def module_cpu_only(self, *args, **kwargs):
    return self.cpu()
torch.nn.Module.cuda = module_cpu_only
# ── Config réseau (copie de config.py TiCNet) ────────────────────────────────

def get_anchors(bases, aspect_ratios):
    anchors = []
    for b in bases:
        for asp in aspect_ratios:
            d, h, w = b * asp[0], b * asp[1], b * asp[2]
            anchors.append([d, h, w])
    return anchors


NET_CONFIG = {
    'anchors': get_anchors([5, 10, 20, 30, 50], [[1, 1, 1]]),
    'roi_names': ['nodule'],
    'pad_value': 170,
    'crop_size': [128, 128, 128],
    'bbox_border': 8,
    'stride': 4,
    'max_stride': 16,
    'num_neg': 800,
    'th_neg': 0.02,
    'th_pos_train': 0.5,
    'th_pos_val': 1,
    'num_hard': 3,
    'bound_size': 12,
    'blacklist': [],
    'num_class': 2,
    'aux_loss': False,
    'augtype': {'flip': True, 'rotate': True, 'scale': True, 'swap': False},
    'r_rand_crop': 0.,
    'rpn_train_bg_thresh_high': 0.02,
    'rpn_train_fg_thresh_low': 0.5,
    'rpn_train_nms_num': 300,
    'rpn_train_nms_pre_score_threshold': 0.5,
    'rpn_train_nms_overlap_threshold': 0.1,
    'rpn_test_nms_pre_score_threshold': 0.5,
    'rpn_test_nms_overlap_threshold': 0.1,
    'rcnn_crop_size': (7, 7, 7),
    'rcnn_train_fg_thresh_low': 0.5,
    'rcnn_train_bg_thresh_high': 0.1,
    'rcnn_train_batch_size': 64,
    'rcnn_train_fg_fraction': 0.5,
    'rcnn_train_nms_pre_score_threshold': 0.5,
    'rcnn_train_nms_overlap_threshold': 0.1,
    'rcnn_test_nms_pre_score_threshold': 0.0,
    'rcnn_test_nms_overlap_threshold': 0.1,
    'box_reg_weight': [1., 1., 1., 1., 1., 1.],
    'hidden_dim': 64,
    'dropout': 0.1,
    'nheads': 8,
    'dim_feedforward': 256,
    'enc_layers': 6,
    'dec_layers': 6,
    'pre_norm': '',
    'return_intermediate_dec': True,
    'position_embedding': 'sine',
    'num_queries': 512,
}


# ── Chargement du modèle (singleton) ─────────────────────────────────────────

_model = None


_model = None

def load_model(pth_path: str):
    global _model
    _model = None  # ← force rechargement à chaque fois (temporaire pour debug)

    print(f"[TiCNet] Loading model from {pth_path} on CPU...")
    _model = build_model(NET_CONFIG)
    _model = _model.cpu()

    checkpoint = torch.load(pth_path, map_location=torch.device('cpu'))
    _model.load_state_dict(checkpoint['state_dict'])
    _model.eval()

    # ── DEBUG architecture ──────────────────────────────
    total_params = sum(p.numel() for p in _model.parameters())
    print(f"[TiCNet] Nombre de paramètres : {total_params:,}")
    print(f"[TiCNet] Epoch du checkpoint   : {checkpoint.get('epoch', 'N/A')}")
    # ────────────────────────────────────────────────────

    print("[TiCNet] Model loaded.")
    return _model


# def read_ct_file(filepath: str) -> np.ndarray:
#     ext = os.path.splitext(filepath)[1].lower()

#     if ext == '.npy':
#         arr = np.load(filepath).astype(np.float32)
#         print(f"[TiCNet] Fichier .npy lu : shape={arr.shape}")
#         print(f"[TiCNet] Min={arr.min()}, Max={arr.max()}")
#         return arr  # ← retourne brut, normalisation dans preprocess

#     elif ext == '.nrrd':
#         arr, _ = nrrd.read(filepath)
#         arr = arr.astype(np.float32)
#         print(f"[TiCNet] Fichier .nrrd lu : shape={arr.shape}")
#         return arr  # ← retourne brut, normalisation dans preprocess

#     elif ext == '.zip':
#         arr, spacing = _read_dicom_zip(filepath)
#         arr = _resample_to_1mm(arr, spacing)
#         # Convertit HU → uint8 exactement comme HU2uint8 dans preprocess.py
#         arr = np.clip(arr, -1200, 600)
#         arr = (arr - (-1200)) / (600 - (-1200))
#         arr = (arr * 255).astype(np.float32)
#         return arr

#     elif ext in ['.mhd', '.nii', '.nii.gz']:
#         itk_img = sitk.ReadImage(filepath)
#         arr = sitk.GetArrayFromImage(itk_img).astype(np.float32)
#         spacing = list(reversed(itk_img.GetSpacing()))
#         arr = _resample_to_1mm(arr, spacing)
#         arr = np.clip(arr, -1200, 600)
#         arr = (arr - (-1200)) / (600 - (-1200))
#         arr = (arr * 255).astype(np.float32)
#         return arr

#     elif ext == '.dcm':
#         itk_img = sitk.ReadImage(filepath)
#         arr = sitk.GetArrayFromImage(itk_img).astype(np.float32)
#         spacing = list(reversed(itk_img.GetSpacing()))
#         arr = _resample_to_1mm(arr, spacing)
#         arr = np.clip(arr, -1200, 600)
#         arr = (arr - (-1200)) / (600 - (-1200))
#         arr = (arr * 255).astype(np.float32)
#         return arr

#     elif ext in ['.png', '.jpg', '.jpeg']:
#         from PIL import Image
#         img = Image.open(filepath).convert('L')
#         arr = np.array(img, dtype=np.float32)
#         arr = arr[np.newaxis, ...]
#         return arr

#     else:
#         raise ValueError(f"Format non supporté : {ext}")

def read_ct_file(filepath: str) -> np.ndarray:
    """
    Lit un fichier CT et retourne un array numpy prêt pour TiCNet.
    
    Formats supportés :
    - .zip  → série DICOM → preprocessing complet (resample+masque+crop)
    - .nrrd → fichier préprocessé TiCNet (_seg.nrrd)
    - .npy  → fichier préprocessé TiCNet (.npy uint8)
    - .mhd  → CT scan MHD → preprocessing complet
    - .dcm  → DICOM unique → preprocessing simplifié
    """
    from analyse.preprocessing import preprocess_dicom_zip, resample, HU2uint8

    ext = os.path.splitext(filepath)[1].lower()

    # ── ZIP DICOM — preprocessing complet ───────────────
    if ext == '.zip':
        print(f"[TiCNet] Preprocessing DICOM ZIP complet...")
        arr = preprocess_dicom_zip(filepath)
        print(f"[TiCNet] Volume préprocessé : shape={arr.shape}, min={arr.min():.1f}, max={arr.max():.1f}")
        return arr

    # ── .nrrd — fichier _seg.nrrd TiCNet (déjà préprocessé) ──
    elif ext == '.nrrd':
        arr, _ = nrrd.read(filepath)
        arr    = arr.astype(np.float32)
        print(f"[TiCNet] Fichier .nrrd lu : shape={arr.shape}")
        return arr

    # ── .npy — fichier préprocessé TiCNet (uint8) ───────
    elif ext == '.npy':
        arr = np.load(filepath).astype(np.float32)
        print(f"[TiCNet] Fichier .npy lu : shape={arr.shape}, min={arr.min()}, max={arr.max()}")
        return arr

    # ── .mhd / .nii — preprocessing complet ─────────────
    elif ext in ['.mhd', '.nii', '.nii.gz']:
        itk_img = sitk.ReadImage(filepath)
        arr     = sitk.GetArrayFromImage(itk_img).astype(np.float32)
        spacing = np.array(list(reversed(itk_img.GetSpacing())))
        print(f"[TiCNet] Fichier {ext} lu : shape={arr.shape}, spacing={spacing}")
        arr, _  = resample(arr, spacing)
        arr     = HU2uint8(arr).astype(np.float32)
        return arr

    # ── .dcm unique ──────────────────────────────────────
    elif ext == '.dcm':
        itk_img = sitk.ReadImage(filepath)
        arr     = sitk.GetArrayFromImage(itk_img).astype(np.float32)
        spacing = np.array(list(reversed(itk_img.GetSpacing())))
        arr, _  = resample(arr, spacing)
        arr     = HU2uint8(arr).astype(np.float32)
        return arr

    else:
        raise ValueError(f"Format non supporté : {ext}")
def preprocess_for_inference(arr: np.ndarray) -> torch.Tensor:
    from scipy.ndimage import zoom
    import math

    # pad2factor — exactement comme BboxReader.eval
    def pad2factor(image, factor=16, pad_value=0):
        depth, height, width = image.shape
        d = int(math.ceil(depth / float(factor))) * factor
        h = int(math.ceil(height / float(factor))) * factor
        w = int(math.ceil(width / float(factor))) * factor
        pad = [[0, d - depth], [0, h - height], [0, w - width]]
        return np.pad(image, pad, 'constant', constant_values=pad_value)

    # Prend le volume 3D
    volume = arr if arr.ndim == 3 else arr[0]

    # pad2factor comme BboxReader
    volume = pad2factor(volume, factor=16, pad_value=170)

    # Normalisation exacte de BboxReader : (x - 128) / 128
    volume = (volume.astype(np.float32) - 128.) / 128.

    print(f"[TiCNet] After pad2factor shape : {volume.shape}")
    print(f"[TiCNet] After normalization min={volume.min():.3f}, max={volume.max():.3f}")

    # Ajoute dimensions batch et canal
    tensor = torch.from_numpy(volume).float()
    tensor = tensor.unsqueeze(0).unsqueeze(0)
    return tensor
def _read_dicom_zip(zip_filepath: str):
    """Retourne (array, spacing)"""
    import tempfile, zipfile

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_filepath, 'r') as zf:
            zf.extractall(tmpdir)

        dcm_files = []
        for root, dirs, files in os.walk(tmpdir):
            for f in files:
                if f.lower().endswith('.dcm') or _is_dicom(os.path.join(root, f)):
                    dcm_files.append(os.path.join(root, f))

        if not dcm_files:
            raise ValueError("Aucun fichier DICOM trouvé dans le ZIP.")

        print(f"[TiCNet] {len(dcm_files)} fichiers DICOM trouvés.")
        dicom_dir = os.path.dirname(dcm_files[0])

        reader    = sitk.ImageSeriesReader()
        series_ids = reader.GetGDCMSeriesIDs(dicom_dir)

        if not series_ids:
            raise ValueError("Aucune série DICOM valide trouvée.")

        dicom_series = reader.GetGDCMSeriesFileNames(dicom_dir, series_ids[0])
        reader.SetFileNames(dicom_series)
        itk_img = reader.Execute()

        arr     = sitk.GetArrayFromImage(itk_img).astype(np.float32)
        spacing = list(reversed(itk_img.GetSpacing()))  # → [Z_spacing, Y_spacing, X_spacing]

        print(f"[TiCNet] Volume DICOM lu : shape={arr.shape}, spacing={spacing}")
        return arr, spacing


def _resample_to_1mm(arr: np.ndarray, spacing: list) -> np.ndarray:
    """
    Resample le volume pour que chaque voxel = 1mm.
    C'est exactement ce que fait preprocess.py de LUNA16.
    """
    from scipy.ndimage import zoom

    spacing = np.array(spacing, dtype=np.float32)
    new_shape = np.round(arr.shape * spacing).astype(int)
    scale     = new_shape / np.array(arr.shape)

    print(f"[TiCNet] Resample : {arr.shape} → {tuple(new_shape)} (spacing={spacing})")
    arr_resampled = zoom(arr, scale, order=1)
    return arr_resampled


def apply_nms(detections: list, threshold: float = 0.1) -> list:
    # ← vérifie taille avant tout
    if not detections or len(detections) == 0:
        return []

    pd = np.array(detections, dtype=np.float32)

    # ← vérifie que l'array n'est pas vide
    if pd.size == 0 or pd.ndim < 2 or pd.shape[0] == 0:
        return []

    x1 = pd[:, 0] - pd[:, 3]
    y1 = pd[:, 1] - pd[:, 3]
    z1 = pd[:, 2] - pd[:, 3]
    x2 = pd[:, 0] + pd[:, 3]
    y2 = pd[:, 1] + pd[:, 3]
    z2 = pd[:, 2] + pd[:, 3]
    scores = pd[:, 4]
    order  = scores.argsort()[::-1]
    areas  = (x2 - x1 + 1) * (y2 - y1 + 1) * (z2 - z1 + 1)
    keep   = []

    while order.size > 0:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        zz1 = np.maximum(z1[i], z1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        zz2 = np.minimum(z2[i], z2[order[1:]])
        inter = (np.maximum(0., xx2 - xx1 + 1) *
                 np.maximum(0., yy2 - yy1 + 1) *
                 np.maximum(0., zz2 - zz1 + 1))
        iou   = inter / (areas[i] + areas[order[1:]] - inter)
        inds  = np.where(iou <= threshold)[0]
        order = order[inds + 1]

    return pd[keep].tolist()



    



def run_inference(pth_path: str, ct_filepath: str, output_dir: str):
    import numpy as np
    os.makedirs(output_dir, exist_ok=True)

    # 1. Charge modèle
    model = load_model(pth_path)

    # 2. Lit CT
    arr = read_ct_file(ct_filepath)

    # ── DEBUG ──────────────────────────────────────────
    print(f"[DEBUG] Shape du volume    : {arr.shape}")
    print(f"[DEBUG] Min valeur         : {arr.min():.4f}")
    print(f"[DEBUG] Max valeur         : {arr.max():.4f}")
    print(f"[DEBUG] Moyenne            : {arr.mean():.4f}")
    # ───────────────────────────────────────────────────

    # 3. Préprocessing
    tensor = preprocess_for_inference(arr)

    # ── DEBUG ──────────────────────────────────────────
    print(f"[DEBUG] Shape tensor       : {tensor.shape}")
    # ───────────────────────────────────────────────────

    # 4. Inférence CPU
    model.use_rcnn = True
    model.set_mode('eval')

    with torch.no_grad():
        truth_bboxes = np.array([[]])
        truth_labels = np.array([[]])
        model.forward(tensor, truth_bboxes, truth_labels)

    # ── DEBUG scores bruts RPN ──────────────────────────
    rpn_logits = model.rpn_logits_flat.detach().numpy()
    rpn_scores = 1 / (1 + np.exp(-rpn_logits))  # sigmoid
    print(f"[DEBUG] RPN logits shape    : {rpn_logits.shape}")
    print(f"[DEBUG] RPN scores max      : {rpn_scores.max():.4f}")
    print(f"[DEBUG] RPN scores mean     : {rpn_scores.mean():.4f}")
    print(f"[DEBUG] RPN scores > 0.1    : {(rpn_scores > 0.1).sum()}")
    print(f"[DEBUG] RPN scores > 0.05   : {(rpn_scores > 0.05).sum()}")
    print(f"[DEBUG] RPN scores > 0.01   : {(rpn_scores > 0.01).sum()}")
    # ────────────────────────────────────────────────────

    # 5. Récupère les résultats
    ensembles = model.ensemble_proposals.detach().numpy()

    # ── DEBUG ──────────────────────────────────────────
    print(f"[DEBUG] Ensemble shape     : {ensembles.shape}")
    print(f"[DEBUG] Ensemble proposals : {ensembles[:5]}")
    print(f"[DEBUG] RPN proposals      : {len(model.rpn_proposals)}")
    if len(ensembles) > 0:
        print(f"[DEBUG] Probabilités max   : {ensembles[:, 1].max():.4f}")
        print(f"[DEBUG] Probabilités min   : {ensembles[:, 1].min():.4f}")
        print(f"[DEBUG] > 0.5             : {(ensembles[:, 1] > 0.5).sum()}")
        print(f"[DEBUG] > 0.3             : {(ensembles[:, 1] > 0.3).sum()}")
        print(f"[DEBUG] > 0.1             : {(ensembles[:, 1] > 0.1).sum()}")
    # ───────────────────────────────────────────────────

    # 6. Filtre par seuil de probabilité
    detections = []
    for det in ensembles:
        if det[1] > 0.5:
            detections.append([
                float(det[4]),  # coordX
                float(det[3]),  # coordY
                float(det[2]),  # coordZ
                float(det[5]),  # diameter_mm
                float(det[1]),  # probability
            ])

    # ── DEBUG ──────────────────────────────────────────
    print(f"[DEBUG] Détections > 0.5   : {len(detections)}")
    # ───────────────────────────────────────────────────

    # 7. NMS
    detections = apply_nms(detections, threshold=0.1)

    # 8. Génère visualisations
    slices_dir = os.path.join(output_dir, 'slices')
    _generate_visualizations(arr, detections, slices_dir)

    # 9. Résultats structurés
    nodules = []
    for det in detections:
        nodules.append({
            'coordX':      round(det[0], 2),
            'coordY':      round(det[1], 2),
            'coordZ':      round(det[2], 2),
            'diameter_mm': round(det[3], 2),
            'probability': round(det[4], 4),
            'risk':        _get_risk_level(det[4]),
        })

    return {
        'nodule_count':    len(nodules),
        'nodules':         nodules,
        'max_probability': max([n['probability'] for n in nodules], default=0.0),
        'slices_dir':      slices_dir,
    }
# ── Visualisation ─────────────────────────────────────────────────────────────

# def _generate_visualizations(arr: np.ndarray, detections: list, slices_dir: str):
#     """
#     Génère les slices PNG avec les boîtes de détection dessinées.
#     Sauvegarde uniquement les slices qui contiennent des détections.
#     """
#     os.makedirs(slices_dir, exist_ok=True)

#     # Normalise pour l'affichage
#     volume = arr if arr.ndim == 3 else arr[0]
#     volume = np.clip(volume, 0, 1)

#     if not detections:
#         # Pas de détection — sauvegarde slice du milieu
#         mid = volume.shape[0] // 2
#         _save_slice(volume[mid], mid, [], slices_dir)
#         return

#     # Trouve les slices concernées par les détections
#     affected_slices = set()
#     for det in detections:
#         z, d = det[2], det[3]
#         start = max(0, int(z - d / 2))
#         end   = min(volume.shape[0] - 1, int(z + d / 2))
#         for s in range(start, end + 1):
#             affected_slices.add(s)

#     for i in affected_slices:
#         slice_dets = []
#         for det in detections:
#             z, d = det[2], det[3]
#             if int(z - d / 2) <= i <= int(z + d / 2):
#                 slice_dets.append(det)
#         _save_slice(volume[i], i, slice_dets, slices_dir)
def _generate_visualizations(arr: np.ndarray, detections: list, slices_dir: str):
    os.makedirs(slices_dir, exist_ok=True)

    volume = arr if arr.ndim == 3 else arr[0]

    # ── CORRECTION : normalise [0,255] → [0,1] pour l'affichage ──
    v_min, v_max = volume.min(), volume.max()
    if v_max > v_min:
        volume = (volume - v_min) / (v_max - v_min)
    else:
        volume = np.zeros_like(volume)
    # ──────────────────────────────────────────────────────────────

    if not detections:
        mid = volume.shape[0] // 2
        _save_slice(volume[mid], mid, [], slices_dir)
        return

    affected_slices = set()
    for det in detections:
        z, d = det[2], det[3]
        start = max(0, int(z - d / 2))
        end   = min(volume.shape[0] - 1, int(z + d / 2))
        for s in range(start, end + 1):
            affected_slices.add(s)

    for i in affected_slices:
        slice_dets = [det for det in detections
                      if int(det[2] - det[3]/2) <= i <= int(det[2] + det[3]/2)]
        _save_slice(volume[i], i, slice_dets, slices_dir)

def _save_slice(slice_arr: np.ndarray, idx: int, detections: list, out_dir: str):
    fig, ax = plt.subplots(1, figsize=(6, 6))
    ax.imshow(slice_arr, cmap='bone')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')

    for det in detections:
        x, y, d, prob = det[0], det[1], det[3], det[4]
        rect = patches.Rectangle(
            (x - d / 2, y - d / 2), d, d,
            linewidth=2, edgecolor='white', facecolor='none'
        )
        ax.add_patch(rect)
        ax.text(
            x - d / 2, y - d / 2 - 2,
            f'{prob:.2f}',
            color='white', fontsize=7,
            bbox=dict(facecolor='black', alpha=0.4, pad=1)
        )

    plt.tight_layout(pad=0)
    plt.savefig(os.path.join(out_dir, f'slice_{idx:04d}.png'), dpi=100, bbox_inches='tight')
    plt.close()


def _get_risk_level(probability: float) -> str:
    if probability >= 0.85:
        return "CRITIQUE"
    elif probability >= 0.70:
        return "ELEVE"
    elif probability >= 0.50:
        return "MODERE"
    else:
        return "FAIBLE"