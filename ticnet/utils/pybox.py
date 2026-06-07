# import torch
# import numpy as np
# from box import cpu_nms, cpu_overlap


# def torch_nms(dets, thresh):
#     """
#     dets has to be a tensor
#     """
#     if isinstance(dets, np.ndarray):
#         dets = torch.from_numpy(dets).float().contiguous()

#     if not dets.is_cuda:
#         z = dets[:, 1]
#         y = dets[:, 2]
#         x = dets[:, 3]
#         d = dets[:, 4]
#         h = dets[:, 5]
#         w = dets[:, 6]
#         scores = dets[:, 0]

#         areas = d * h * w
#         order = scores.sort(0, descending=True)[1]
#         # order = torch.from_numpy(np.ascontiguousarray(scores.numpy().argsort()[::-1])).long()

#         keep = torch.LongTensor(dets.size(0))
#         num_out = torch.LongTensor(1)
#         cpu_nms(keep, num_out, dets, order, areas, thresh)

#         return dets[keep[:num_out[0]]], keep[:num_out[0]]

#     else:
#         raise NotImplementedError


# def torch_overlap(boxes1, boxes2):
#     """
#     dets has to be a tensor
#     """
#     if isinstance(boxes1, np.ndarray):
#         boxes1 = torch.from_numpy(boxes1).float().contiguous()
#     if isinstance(boxes2, np.ndarray):
#         boxes2 = torch.from_numpy(boxes2).float().contiguous()

#     if not boxes1.is_cuda and not boxes2.is_cuda:
#         assert isinstance(boxes1, torch.FloatTensor) and isinstance(boxes2, torch.FloatTensor)
#         overlap = torch.zeros([len(boxes1), len(boxes2)], dtype=torch.float32)
#         cpu_overlap(boxes1, boxes2, overlap)

#         return overlap
#     else:
#         raise NotImplementedError
# import torch
# import numpy as np


# def torch_nms(dets, thresh):
#     """
#     dets has to be a tensor
#     Pure Python/NumPy replacement for cpu_nms
#     """
#     if isinstance(dets, np.ndarray):
#         dets = torch.from_numpy(dets).float().contiguous()

#     if not dets.is_cuda:
#         z = dets[:, 1].numpy()
#         y = dets[:, 2].numpy()
#         x = dets[:, 3].numpy()
#         d = dets[:, 4].numpy()
#         h = dets[:, 5].numpy()
#         w = dets[:, 6].numpy()
#         scores = dets[:, 0].numpy()

#         z1 = z - d / 2
#         z2 = z + d / 2
#         y1 = y - h / 2
#         y2 = y + h / 2
#         x1 = x - w / 2
#         x2 = x + w / 2

#         areas = d * h * w
#         order = scores.argsort()[::-1]

#         keep = []
#         while order.size > 0:
#             i = order[0]
#             keep.append(i)

#             iz1 = np.maximum(z1[i], z1[order[1:]])
#             iz2 = np.minimum(z2[i], z2[order[1:]])
#             iy1 = np.maximum(y1[i], y1[order[1:]])
#             iy2 = np.minimum(y2[i], y2[order[1:]])
#             ix1 = np.maximum(x1[i], x1[order[1:]])
#             ix2 = np.minimum(x2[i], x2[order[1:]])

#             id = np.maximum(0.0, iz2 - iz1)
#             ih = np.maximum(0.0, iy2 - iy1)
#             iw = np.maximum(0.0, ix2 - ix1)

#             inter = id * ih * iw
#             iou = inter / (areas[i] + areas[order[1:]] - inter)

#             inds = np.where(iou <= thresh)[0]
#             order = order[inds + 1]

#         keep = torch.LongTensor(keep)
#         return dets[keep], keep

#     else:
#         raise NotImplementedError


# def torch_overlap(boxes1, boxes2):
#     """
#     Pure Python/NumPy replacement for cpu_overlap
#     Computes 3D IoU overlap between two sets of boxes
#     """
#     if isinstance(boxes1, np.ndarray):
#         boxes1 = torch.from_numpy(boxes1).float().contiguous()
#     if isinstance(boxes2, np.ndarray):
#         boxes2 = torch.from_numpy(boxes2).float().contiguous()

#     if not boxes1.is_cuda and not boxes2.is_cuda:
#         b1 = boxes1.numpy()
#         b2 = boxes2.numpy()

#         overlap = np.zeros((len(b1), len(b2)), dtype=np.float32)

#         for i in range(len(b1)):
#             z1_i = b1[i, 0] - b1[i, 3] / 2
#             z2_i = b1[i, 0] + b1[i, 3] / 2
#             y1_i = b1[i, 1] - b1[i, 4] / 2
#             y2_i = b1[i, 1] + b1[i, 4] / 2
#             x1_i = b1[i, 2] - b1[i, 5] / 2
#             x2_i = b1[i, 2] + b1[i, 5] / 2
#             area_i = b1[i, 3] * b1[i, 4] * b1[i, 5]

#             for j in range(len(b2)):
#                 z1_j = b2[j, 0] - b2[j, 3] / 2
#                 z2_j = b2[j, 0] + b2[j, 3] / 2
#                 y1_j = b2[j, 1] - b2[j, 4] / 2
#                 y2_j = b2[j, 1] + b2[j, 4] / 2
#                 x1_j = b2[j, 2] - b2[j, 5] / 2
#                 x2_j = b2[j, 2] + b2[j, 5] / 2
#                 area_j = b2[j, 3] * b2[j, 4] * b2[j, 5]

#                 id = max(0.0, min(z2_i, z2_j) - max(z1_i, z1_j))
#                 ih = max(0.0, min(y2_i, y2_j) - max(y1_i, y1_j))
#                 iw = max(0.0, min(x2_i, x2_j) - max(x1_i, x1_j))

#                 inter = id * ih * iw
#                 overlap[i, j] = inter / (area_i + area_j - inter)

#         return torch.from_numpy(overlap)

#     else:
#         raise NotImplementedError

"""
utils/util.py
=============
Pure Python/NumPy replacement for the C++ pybox module.
Fonctionne sur Windows sans compilation.

Remplace :
    from ticnet.utils.pybox import torch_nms, torch_overlap
par :
    from ticnet.utils.util import torch_nms, torch_overlap
"""

import torch
import numpy as np


def torch_nms(dets, thresh):
    """
    3D Non-Maximum Suppression — Pure Python/NumPy.

    Args:
        dets  : Tensor ou ndarray shape (N, 7)
                colonnes : [score, z, y, x, d, h, w]
        thresh: float, seuil IoU

    Returns:
        (dets_kept, keep_indices)
    """
    # ── Conversion entrée ────────────────────────────────────────────────────
    if isinstance(dets, np.ndarray):
        dets = torch.from_numpy(dets).float().contiguous()

    # ── Cas vide ─────────────────────────────────────────────────────────────
    if dets.shape[0] == 0:
        return torch.zeros((0, dets.shape[1])), torch.LongTensor([])

    if dets.is_cuda:
        raise NotImplementedError(
            "torch_nms Python fallback ne supporte pas CUDA. "
            "Déplacez les tenseurs sur CPU avant d'appeler NMS."
        )

    # ── Extraction des colonnes ───────────────────────────────────────────────
    scores = dets[:, 0].numpy()
    z      = dets[:, 1].numpy()
    y      = dets[:, 2].numpy()
    x      = dets[:, 3].numpy()
    d      = dets[:, 4].numpy()
    h      = dets[:, 5].numpy()
    w      = dets[:, 6].numpy()

    z1 = z - d / 2;  z2 = z + d / 2
    y1 = y - h / 2;  y2 = y + h / 2
    x1 = x - w / 2;  x2 = x + w / 2

    areas = d * h * w
    # Protège contre volumes nuls
    areas = np.maximum(areas, 1e-6)

    order = scores.argsort()[::-1]
    keep  = []

    while order.size > 0:
        i = order[0]
        keep.append(i)

        if order.size == 1:
            break

        rest = order[1:]

        # Intersection
        iz = np.maximum(0.0, np.minimum(z2[i], z2[rest]) - np.maximum(z1[i], z1[rest]))
        iy = np.maximum(0.0, np.minimum(y2[i], y2[rest]) - np.maximum(y1[i], y1[rest]))
        ix = np.maximum(0.0, np.minimum(x2[i], x2[rest]) - np.maximum(x1[i], x1[rest]))
        inter = iz * iy * ix

        # IoU 3D
        denom = areas[i] + areas[rest] - inter
        denom = np.maximum(denom, 1e-6)  # évite division par zéro
        iou   = inter / denom

        # Garde uniquement les boîtes sous le seuil
        inds  = np.where(iou <= thresh)[0]
        order = order[inds + 1]

    # ── Résultat ─────────────────────────────────────────────────────────────
    if len(keep) == 0:
        return torch.zeros((0, dets.shape[1])), torch.LongTensor([])

    keep = torch.LongTensor(keep)
    return dets[keep], keep


def torch_overlap(boxes1, boxes2):
    """
    Calcule la matrice IoU 3D entre deux ensembles de boîtes.

    Args:
        boxes1 : Tensor ou ndarray shape (N, 6) — [z, y, x, d, h, w]
        boxes2 : Tensor ou ndarray shape (M, 6) — [z, y, x, d, h, w]

    Returns:
        overlap : Tensor shape (N, M) — matrice IoU
    """
    # ── Conversion entrée ────────────────────────────────────────────────────
    if isinstance(boxes1, np.ndarray):
        boxes1 = torch.from_numpy(boxes1).float().contiguous()
    if isinstance(boxes2, np.ndarray):
        boxes2 = torch.from_numpy(boxes2).float().contiguous()

    # ── Cas vide ─────────────────────────────────────────────────────────────
    if boxes1.shape[0] == 0 or boxes2.shape[0] == 0:
        return torch.zeros((boxes1.shape[0], boxes2.shape[0]))

    if boxes1.is_cuda or boxes2.is_cuda:
        raise NotImplementedError(
            "torch_overlap Python fallback ne supporte pas CUDA. "
            "Déplacez les tenseurs sur CPU avant d'appeler overlap."
        )

    b1 = boxes1.numpy()
    b2 = boxes2.numpy()
    N  = len(b1)
    M  = len(b2)

    overlap = np.zeros((N, M), dtype=np.float32)

    # ── Vectorisé sur j pour chaque i ────────────────────────────────────────
    # b1[i] : [z, y, x, d, h, w]
    for i in range(N):
        z1_i = b1[i, 0] - b1[i, 3] / 2;  z2_i = b1[i, 0] + b1[i, 3] / 2
        y1_i = b1[i, 1] - b1[i, 4] / 2;  y2_i = b1[i, 1] + b1[i, 4] / 2
        x1_i = b1[i, 2] - b1[i, 5] / 2;  x2_i = b1[i, 2] + b1[i, 5] / 2
        area_i = b1[i, 3] * b1[i, 4] * b1[i, 5]
        area_i = max(area_i, 1e-6)

        # Vectorisé sur tous les j en même temps
        z1_j = b2[:, 0] - b2[:, 3] / 2;  z2_j = b2[:, 0] + b2[:, 3] / 2
        y1_j = b2[:, 1] - b2[:, 4] / 2;  y2_j = b2[:, 1] + b2[:, 4] / 2
        x1_j = b2[:, 2] - b2[:, 5] / 2;  x2_j = b2[:, 2] + b2[:, 5] / 2
        area_j = b2[:, 3] * b2[:, 4] * b2[:, 5]
        area_j = np.maximum(area_j, 1e-6)

        id_ = np.maximum(0.0, np.minimum(z2_i, z2_j) - np.maximum(z1_i, z1_j))
        ih_ = np.maximum(0.0, np.minimum(y2_i, y2_j) - np.maximum(y1_i, y1_j))
        iw_ = np.maximum(0.0, np.minimum(x2_i, x2_j) - np.maximum(x1_i, x1_j))
        inter = id_ * ih_ * iw_

        denom = area_i + area_j - inter
        denom = np.maximum(denom, 1e-6)
        overlap[i, :] = inter / denom

    return torch.from_numpy(overlap)


# ── Alias pour compatibilité avec pybox ──────────────────────────────────────
cpu_nms     = torch_nms
cpu_overlap = torch_overlap


# ── Test rapide ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Test torch_nms ...")
    # [score, z, y, x, d, h, w]
    dets = torch.tensor([
        [0.9, 10, 10, 10, 8, 8, 8],
        [0.8, 11, 11, 11, 8, 8, 8],   # overlap élevé avec #0
        [0.7, 50, 50, 50, 8, 8, 8],   # loin → gardé
    ], dtype=torch.float32)

    kept_dets, kept_idx = torch_nms(dets, thresh=0.1)
    print(f"  Entrée : {dets.shape[0]} boîtes")
    print(f"  Gardées : {kept_dets.shape[0]} boîtes → indices {kept_idx.tolist()}")
    assert kept_dets.shape[0] == 2, "Attendu 2 boîtes après NMS"

    print("\nTest torch_overlap ...")
    boxes1 = torch.tensor([[10, 10, 10, 8, 8, 8]], dtype=torch.float32)
    boxes2 = torch.tensor([
        [10, 10, 10, 8, 8, 8],   # identique → IoU = 1.0
        [50, 50, 50, 8, 8, 8],   # loin       → IoU = 0.0
    ], dtype=torch.float32)

    ovlp = torch_overlap(boxes1, boxes2)
    print(f"  IoU avec identique : {ovlp[0, 0]:.4f}  (attendu 1.0)")
    print(f"  IoU avec loin      : {ovlp[0, 1]:.4f}  (attendu 0.0)")
    assert abs(ovlp[0, 0].item() - 1.0) < 1e-4
    assert abs(ovlp[0, 1].item() - 0.0) < 1e-4

    print("\nTest cas vide ...")
    empty = torch.zeros((0, 7))
    r, idx = torch_nms(empty, thresh=0.1)
    assert r.shape[0] == 0

    print("\nTOUS LES TESTS PASSES — NMS Python prêt pour Windows")
