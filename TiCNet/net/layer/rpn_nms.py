import itertools
import numpy as np
import torch
from torch.autograd import Variable
from net.layer.util import box_transform, box_transform_inv, clip_boxes


def py_nms(output, nms_overlap_threshold):
    """
    Pure numpy/torch NMS implementation — remplace torch_nms supprimé.
    output: tensor [N, 7] → [prob, z, y, x, d, h, w]
    """
    if len(output) == 0:
        return output, []

    output_np = output.numpy()
    probs = output_np[:, 0]
    z = output_np[:, 1]
    y = output_np[:, 2]
    x = output_np[:, 3]
    d = output_np[:, 4]
    h = output_np[:, 5]
    w = output_np[:, 6]

    z1 = z - d / 2
    y1 = y - h / 2
    x1 = x - w / 2
    z2 = z + d / 2
    y2 = y + h / 2
    x2 = x + w / 2

    areas = d * h * w
    order = probs.argsort()[::-1]
    keep  = []

    while order.size > 0:
        i = order[0]
        keep.append(i)

        if order.size == 1:
            break

        iz1 = np.maximum(z1[i], z1[order[1:]])
        iy1 = np.maximum(y1[i], y1[order[1:]])
        ix1 = np.maximum(x1[i], x1[order[1:]])
        iz2 = np.minimum(z2[i], z2[order[1:]])
        iy2 = np.minimum(y2[i], y2[order[1:]])
        ix2 = np.minimum(x2[i], x2[order[1:]])

        inter = (np.maximum(0., iz2 - iz1) *
                 np.maximum(0., iy2 - iy1) *
                 np.maximum(0., ix2 - ix1))
        iou   = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

        inds  = np.where(iou <= nms_overlap_threshold)[0]
        order = order[inds + 1]

    keep_tensor = torch.from_numpy(np.array(keep))
    return output[keep_tensor], keep


def make_rpn_windows(f, cfg):
    stride  = cfg['stride']
    anchors = np.asarray(cfg['anchors'])
    offset  = (float(stride) - 1) / 2
    _, _, D, H, W = f.shape
    oz = np.arange(offset, offset + stride * (D - 1) + 1, stride)
    oh = np.arange(offset, offset + stride * (H - 1) + 1, stride)
    ow = np.arange(offset, offset + stride * (W - 1) + 1, stride)

    windows = []
    for z, y, x, a in itertools.product(oz, oh, ow, anchors):
        windows.append([z, y, x, a[0], a[1], a[2]])
    windows = np.array(windows)
    return windows


def rpn_nms(cfg, mode, inputs, window, logits_flat, deltas_flat):
    if mode in ['train']:
        nms_pre_score_threshold = cfg['rpn_train_nms_pre_score_threshold']
        nms_overlap_threshold   = cfg['rpn_train_nms_overlap_threshold']
    elif mode in ['eval', 'valid', 'test']:
        nms_pre_score_threshold = cfg['rpn_test_nms_pre_score_threshold']
        nms_overlap_threshold   = cfg['rpn_test_nms_overlap_threshold']
    else:
        raise ValueError('rpn_nms(): invalid mode = %s?' % mode)

    logits = torch.sigmoid(logits_flat).data.cpu().numpy()
    deltas = deltas_flat.data.cpu().numpy()
    batch_size, _, depth, height, width = inputs.size()

    proposals = []
    for b in range(batch_size):
        proposal = [np.empty((0, 8), np.float32)]

        ps = logits[b, :, 0].reshape(-1, 1)
        ds = deltas[b, :, :]

        index = np.where(ps[:, 0] > nms_pre_score_threshold)[0]
        if len(index) > 0:
            p   = ps[index]
            d   = ds[index]
            w   = window[index]
            box = rpn_decode(w, d, cfg['box_reg_weight'])
            box = clip_boxes(box, inputs.shape[2:])

            output = np.concatenate((p, box), 1)
            output = torch.from_numpy(output)

            # ← py_nms au lieu de torch_nms
            output, keep = py_nms(output, nms_overlap_threshold)

            prop = np.zeros((len(output), 8), np.float32)
            prop[:, 0] = b
            prop[:, 1:8] = output.numpy()
            proposal.append(prop)

        proposal = np.vstack(proposal)
        proposals.append(proposal)

    proposals = np.vstack(proposals)

    if len(proposals) != 0:
        # ← CPU au lieu de .cuda()
        proposals = Variable(torch.from_numpy(proposals))
        return proposals
    else:
        return Variable(torch.rand([0, 8]))


def rpn_encode(window, truth_box, weight):
    return box_transform(window, truth_box, weight)


def rpn_decode(window, delta, weight):
    return box_transform_inv(window, delta, weight)