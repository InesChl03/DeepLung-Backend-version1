
import itertools
import numpy as np
# import torch
# from torch.autograd import Variable
# from net.layer.util import box_transform, box_transform_inv, clip_boxes
# import numpy as np
import torch
import torch.nn.functional as F
from torch.autograd import Variable
from net.layer.util import box_transform, box_transform_inv, clip_boxes


def py_nms(output, nms_overlap_threshold):
    """
    Pure numpy NMS — remplace torch_nms.
    output: tensor [N, 8] → [prob, z, y, x, d, h, w, class]
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


def rcnn_encode(window, truth_box, weight):
    return box_transform(window, truth_box, weight)


def rcnn_decode(window, delta, weight):
    return box_transform_inv(window, delta, weight)


def rcnn_nms(cfg, mode, inputs, proposals, logits, deltas):
    if mode in ['train']:
        nms_pre_score_threshold = cfg['rcnn_train_nms_pre_score_threshold']
        nms_overlap_threshold   = cfg['rcnn_train_nms_overlap_threshold']
    elif mode in ['valid', 'test', 'eval']:
        nms_pre_score_threshold = cfg['rcnn_test_nms_pre_score_threshold']
        nms_overlap_threshold   = cfg['rcnn_test_nms_overlap_threshold']
    else:
        raise ValueError('rcnn_nms(): invalid mode = %s?' % mode)

    batch_size, _, depth, height, width = inputs.size()
    num_class = cfg['num_class']

    probs     = F.softmax(logits, dim=1).cpu().data.numpy()
    deltas    = deltas.cpu().data.numpy().reshape(-1, num_class, 6)
    proposals = proposals.cpu().data.numpy()

    detections = []
    keeps      = []

    for b in range(batch_size):
        detection = [np.empty((0, 9), np.float32)]
        index = np.where(proposals[:, 0] == b)[0]

        if len(index) > 0:
            prob     = probs[index]
            delta    = deltas[index]
            proposal = proposals[index]

            for j in range(1, num_class):
                idx = np.where(prob[:, j] > nms_pre_score_threshold)[0]
                if len(idx) > 0:
                    p   = prob[idx, j].reshape(-1, 1)
                    d   = delta[idx, j]
                    box = rcnn_decode(proposal[idx, 2:8], d, cfg['box_reg_weight'])
                    box = clip_boxes(box, inputs.shape[2:])
                    js  = np.expand_dims(np.array([j] * len(p)), axis=-1)
                    output = np.concatenate((p, box, js), 1)

                    if len(output) > 0:
                        output = torch.from_numpy(output).float()
                        # ← py_nms au lieu de torch_nms
                        output, keep = py_nms(output, nms_overlap_threshold)

                    num = len(output)
                    if num > 0:
                        det = np.zeros((num, 9), np.float32)
                        det[:, 0]  = b
                        det[:, 1:] = output.numpy()
                        detection.append(det)
                        keeps.extend(index[idx[np.array(keep)]].tolist())

        detection = np.vstack(detection)
        detections.append(detection)

    # ← CPU au lieu de .cuda()
    detections = Variable(torch.from_numpy(np.vstack(detections)))
    return detections, keeps


def get_probability(cfg, mode, inputs, proposals, logits, deltas):
    if mode in ['train']:
        nms_pre_score_threshold = cfg['rcnn_train_nms_pre_score_threshold']
    elif mode in ['valid', 'test', 'eval']:
        nms_pre_score_threshold = cfg['rcnn_test_nms_pre_score_threshold']
    else:
        raise ValueError('get_probability(): invalid mode = %s?' % mode)

    num_class = cfg['num_class']
    probs     = F.softmax(logits, dim=1).cpu().data.numpy()
    deltas    = deltas.cpu().data.numpy().reshape(-1, num_class, 6)
    proposals = proposals.cpu().data.numpy()

    output = None
    for j in range(1, num_class):
        idx = np.where(probs[:, j] > nms_pre_score_threshold)[0]
        if len(idx) > 0:
            p   = probs[idx, j].reshape(-1, 1)
            d   = deltas[idx, j]
            box = rcnn_decode(proposals[idx, 2:8], d, cfg['box_reg_weight'])
            box = clip_boxes(box, inputs.shape[2:])
            js  = np.expand_dims(np.array([j] * len(p)), axis=-1)
            output = np.concatenate((p, box, js), 1)

    if output is None:
        output = np.zeros((len(proposals), 8), np.float32)

    # ← CPU au lieu de .cuda()
    return torch.from_numpy(output).float()