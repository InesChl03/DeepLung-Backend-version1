# # import os
# # import sys
# # import shutil
# # import tempfile
# # import numpy as np
# # import torch
# # import SimpleITK as sitk
# # import scipy.ndimage
# # from fastapi import FastAPI, UploadFile, File
# # from fastapi.middleware.cors import CORSMiddleware

# # sys.path.insert(0, '/home/inas/STicnet')
# # os.environ['CUDA_VISIBLE_DEVICES'] = ''

# # from config import net_config
# # from net.main_net import build_model

# # app = FastAPI()

# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["*"],
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )
# # import logging
# # import sys

# # logging.basicConfig(
# #     stream=sys.stdout,
# #     level=logging.INFO,
# #     format='%(asctime)s %(message)s'
# # )
# # logger = logging.getLogger(__name__)
# # # Charger le modèle une seule fois au démarrage
# # print("Loading model...")
# # model = build_model(net_config)
# # checkpoint = torch.load(
# #     '/home/inas/STicnet/results/ticnet/2_fold/model/120.pth',
# #     map_location='cpu'
# # )
# # model.load_state_dict(checkpoint['state_dict'])
# # model.cpu()
# # model.use_rcnn = True
# # model.set_mode('eval')
# # print("Model loaded successfully")


# # def load_itk_image(filename):
# #     itkimage = sitk.ReadImage(filename)
# #     numpyImage = sitk.GetArrayFromImage(itkimage)
# #     numpyOrigin = np.array(list(reversed(itkimage.GetOrigin())))
# #     numpySpacing = np.array(list(reversed(itkimage.GetSpacing())))
# #     return numpyImage, numpyOrigin, numpySpacing


# # def HU2uint8(image, HU_min=-1200.0, HU_max=600.0, HU_nan=-2000.0):
# #     image_new = np.array(image)
# #     image_new[np.isnan(image_new)] = HU_nan
# #     image_new = (image_new - HU_min) / (HU_max - HU_min)
# #     image_new = np.clip(image_new, 0, 1)
# #     image_new = (image_new * 255).astype('uint8')
# #     return image_new


# # def resample(image, spacing, new_spacing=[1.0, 1.0, 1.0]):
# #     new_shape = np.round(np.array(image.shape) * np.array(spacing) / np.array(new_spacing))
# #     resize_factor = new_shape / np.array(image.shape)
# #     image_new = scipy.ndimage.zoom(image, resize_factor, mode='nearest', order=1)
# #     return image_new


# # # def preprocess_single(mhd_path):
# # #     img, origin, spacing = load_itk_image(mhd_path)
# # #     img = HU2uint8(img)
# # #     img = resample(img, spacing)
# # #     img = img[np.newaxis, np.newaxis].astype(np.float32) / 255.0
# # #     return torch.from_numpy(img), origin, spacing

# # def pad_to_factor(image, factor=16, pad_value=170):
# #     """Pad image so each dimension is divisible by factor"""
# #     D, H, W = image.shape
# #     pad_D = (factor - D % factor) % factor
# #     pad_H = (factor - H % factor) % factor
# #     pad_W = (factor - W % factor) % factor
# #     image = np.pad(image, 
# #                    ((0, pad_D), (0, pad_H), (0, pad_W)), 
# #                    mode='constant', 
# #                    constant_values=pad_value)
# #     return image


# # def preprocess_single(mhd_path):
# #     img, origin, spacing = load_itk_image(mhd_path)
# #     img = HU2uint8(img)
# #     img = resample(img, spacing)
# #     img = pad_to_factor(img, factor=16, pad_value=170)  # ← ajout
# #     img = img[np.newaxis, np.newaxis].astype(np.float32) / 255.0
# #     return torch.from_numpy(img), origin, spacing
# # # @app.post("/predict")
# # # async def predict(
# # #     mhd_file: UploadFile = File(...),
# # #     raw_file: UploadFile = File(...)
# # # ):
# # #     tmp_dir = tempfile.mkdtemp()
# # #     try:
# # #         mhd_path = os.path.join(tmp_dir, mhd_file.filename)
# # #         raw_path = os.path.join(tmp_dir, raw_file.filename)

# # #         with open(mhd_path, 'wb') as f:
# # #             f.write(await mhd_file.read())
# # #         with open(raw_path, 'wb') as f:
# # #             f.write(await raw_file.read())

# # #         # Preprocessing
# # #         input_tensor, origin, spacing = preprocess_single(mhd_path)

# # #         # Inference
# # #         with torch.no_grad():
# # #             model.forward(input_tensor, [], [])
# # #             ensembles = model.ensemble_proposals.cpu().numpy()

# # #         # Filtrer les détections avec score > 0.5
# # #         nodules = []
# # #         for det in ensembles:
# # #             score = float(det[1])
# # #             if score > 0.5:
# # #                 nodules.append({
# # #                     "z": float(det[2]),
# # #                     "y": float(det[3]),
# # #                     "x": float(det[4]),
# # #                     "diameter_mm": float(det[5]),
# # #                     "probability": score
# # #                 })

# # #         return {
# # #             "status": "success",
# # #             "nodules_detected": len(nodules),
# # #             "nodules": nodules
# # #         }

# # #     finally:
# # #         shutil.rmtree(tmp_dir)
# # @app.post("/predict")
# # async def predict(
# #     mhd_file: UploadFile = File(...),
# #     raw_file: UploadFile = File(...)
# # ):
# #     tmp_dir = tempfile.mkdtemp()
# #     try:
# #         import time
# #         t0 = time.time()

# #         print(f"[1/5] Réception des fichiers...")
# #         mhd_path = os.path.join(tmp_dir, mhd_file.filename)
# #         raw_path = os.path.join(tmp_dir, raw_file.filename)

# #         with open(mhd_path, 'wb') as f:
# #             f.write(await mhd_file.read())
# #         with open(raw_path, 'wb') as f:
# #             f.write(await raw_file.read())
# #         print(f"    ✓ Fichiers sauvegardés ({time.time()-t0:.1f}s)")

# #         print(f"[2/5] Preprocessing...")
# #         t1 = time.time()
# #         input_tensor, origin, spacing = preprocess_single(mhd_path)
# #         print(f"    ✓ Shape finale : {input_tensor.shape} ({time.time()-t1:.1f}s)")

# #         print(f"[3/5] Inference TiCNet CPU...")
# #         t2 = time.time()
# #         with torch.no_grad():
# #             model.forward(input_tensor, [], [])
# #         print(f"    ✓ Inference terminée ({time.time()-t2:.1f}s)")

# #         print(f"[4/5] Extraction des détections...")
# #         ensembles = model.ensemble_proposals.cpu().numpy()
# #         print(f"    ✓ {len(ensembles)} proposals total")

# #         print(f"[5/5] Filtrage nodules prob > 0.5...")
# #         nodules = []
# #         for det in ensembles:
# #             score = float(det[1])
# #             if score > 0.5:
# #                 nodules.append({
# #                     "z": float(det[2]),
# #                     "y": float(det[3]),
# #                     "x": float(det[4]),
# #                     "diameter_mm": float(det[5]),
# #                     "probability": score
# #                 })

# #         print(f"    ✓ {len(nodules)} nodules détectés")
# #         print(f"TOTAL : {time.time()-t0:.1f}s")

# #         return {
# #             "status": "success",
# #             "nodules_detected": len(nodules),
# #             "nodules": nodules
# #         }

# #     except Exception as e:
# #         import traceback
# #         print(f"ERREUR : {e}")
# #         traceback.print_exc()
# #         return {"error": str(e)}

# #     finally:
# #         shutil.rmtree(tmp_dir)

# # @app.get("/health")
# # def health():
# #     return {"status": "ok", "model": "TiCNet", "device": "cpu"}
# import os
# import sys
# import shutil
# import tempfile
# import time
# import logging
# import numpy as np
# import torch
# import SimpleITK as sitk
# import scipy.ndimage
# from fastapi import FastAPI, UploadFile, File
# from fastapi.middleware.cors import CORSMiddleware

# # Logging
# logging.basicConfig(
#     stream=sys.stdout,
#     level=logging.INFO,
#     format='%(asctime)s %(message)s'
# )
# logger = logging.getLogger(__name__)
# from ticnet.utils.preprocess import (
#     binarize, exclude_corner_middle,
#     volume_filter, exclude_air, fill_hole, apply_mask, get_lung_box
# )

# sys.path.insert(0, '/home/inas/STicnet')
# os.environ['CUDA_VISIBLE_DEVICES'] = ''

# from config import net_config
# from net.main_net import build_model

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Charger le modèle une seule fois au démarrage
# logger.info("Loading model...")
# model = build_model(net_config)
# checkpoint = torch.load(
#     '/home/inas/STicnet/results/ticnet/2_fold/model/120.pth',
#     map_location='cpu'
# )
# model.load_state_dict(checkpoint['state_dict'])
# model.cpu()
# model.use_rcnn = True
# model.set_mode('eval')
# logger.info("Model loaded successfully")


# def load_itk_image(filename):
#     itkimage = sitk.ReadImage(filename)
#     numpyImage = sitk.GetArrayFromImage(itkimage)
#     numpyOrigin = np.array(list(reversed(itkimage.GetOrigin())))
#     numpySpacing = np.array(list(reversed(itkimage.GetSpacing())))
#     return numpyImage, numpyOrigin, numpySpacing


# def HU2uint8(image, HU_min=-1200.0, HU_max=600.0, HU_nan=-2000.0):
#     image_new = np.array(image)
#     image_new[np.isnan(image_new)] = HU_nan
#     image_new = (image_new - HU_min) / (HU_max - HU_min)
#     image_new = np.clip(image_new, 0, 1)
#     image_new = (image_new * 255).astype('uint8')
#     return image_new


# # def resample(image, spacing, new_spacing=[1.0, 1.0, 1.0]):
# #     new_shape = np.round(np.array(image.shape) * np.array(spacing) / np.array(new_spacing))
# #     resize_factor = new_shape / np.array(image.shape)
# #     image_new = scipy.ndimage.zoom(image, resize_factor, mode='nearest', order=1)
# #     return image_new
# def resample(image, spacing, new_spacing=[1.0, 1.0, 1.0], order=1):
#     new_shape = np.round(np.array(image.shape) * np.array(spacing) / np.array(new_spacing))
#     resample_spacing = np.array(spacing) * np.array(image.shape) / new_shape
#     resize_factor = new_shape / np.array(image.shape)
#     image_new = scipy.ndimage.zoom(image, resize_factor, mode='nearest', order=order)
#     return image_new, resample_spacing

# def pad_to_factor(image, factor=16, pad_value=170):
#     D, H, W = image.shape
#     pad_D = (factor - D % factor) % factor
#     pad_H = (factor - H % factor) % factor
#     pad_W = (factor - W % factor) % factor
#     image = np.pad(image,
#                    ((0, pad_D), (0, pad_H), (0, pad_W)),
#                    mode='constant',
#                    constant_values=pad_value)
#     return image


# def preprocess_single(mhd_path):
#     from skimage import measure, morphology
    
#     img, origin, spacing = load_itk_image(mhd_path)
#     logger.info(f"    Shape originale : {img.shape}, spacing : {spacing}")

#     # Générer le masque pulmonaire automatiquement
#     binary_mask = binarize(img, spacing)
#     label = measure.label(binary_mask, connectivity=1)
#     label = exclude_corner_middle(label)
#     label = volume_filter(label, spacing)
#     binary_mask, has_lung = exclude_air(label, spacing)
#     binary_mask = fill_hole(binary_mask)

#     if not has_lung:
#         logger.warning("    ⚠️ Poumons non détectés, utilisation de l'image complète")
#         binary_mask1 = np.ones(img.shape, dtype=bool)
#         binary_mask2 = np.zeros(img.shape, dtype=bool)
#     else:
#         # Séparer gauche/droite : 2 plus grandes composantes
#         label = measure.label(binary_mask, connectivity=1)
#         props = sorted(measure.regionprops(label), key=lambda x: x.area, reverse=True)
#         binary_mask1 = label == props[0].label
#         binary_mask2 = label == props[1].label if len(props) > 1 else np.zeros_like(binary_mask1)

#     # Convertir HU vers uint8
#     img = HU2uint8(img)

#     # Appliquer le masque
#     seg_img = apply_mask(img, binary_mask1, binary_mask2)

#     # Resample vers 1x1x1 mm
#     # seg_img, resampled_spacing = resample(seg_img, spacing, order=3)
#     seg_img, resampled_spacing = resample(seg_img, spacing)
#     logger.info(f"    Shape après resample : {seg_img.shape}")

#     # Crop sur la boite pulmonaire
#     lung_box = get_lung_box(binary_mask, seg_img.shape)
#     z_min, z_max = lung_box[0]
#     y_min, y_max = lung_box[1]
#     x_min, x_max = lung_box[2]
#     seg_img = seg_img[z_min:z_max, y_min:y_max, x_min:x_max]
#     logger.info(f"    Shape après crop : {seg_img.shape}")

#     # Padding multiple de 16
#     seg_img = pad_to_factor(seg_img, factor=16, pad_value=170)
#     logger.info(f"    Shape finale : {seg_img.shape}")

#     # Normalisation exacte comme BboxReader : (x - 128) / 128
#     seg_img = seg_img[np.newaxis, np.newaxis].astype(np.float32)
#     seg_img = (seg_img - 128.0) / 128.0

#     return torch.from_numpy(seg_img), origin, spacing
# @app.post("/predict")
# async def predict(
#     mhd_file: UploadFile = File(...),
#     raw_file: UploadFile = File(...)
# ):
#     tmp_dir = tempfile.mkdtemp()
#     try:
#         t0 = time.time()

#         logger.info("[1/5] Réception des fichiers...")
#         mhd_path = os.path.join(tmp_dir, mhd_file.filename)
#         raw_path = os.path.join(tmp_dir, raw_file.filename)

#         with open(mhd_path, 'wb') as f:
#             f.write(await mhd_file.read())
#         with open(raw_path, 'wb') as f:
#             f.write(await raw_file.read())
#         logger.info(f"    ✓ Fichiers sauvegardés ({time.time()-t0:.1f}s)")

#         logger.info("[2/5] Preprocessing...")
#         t1 = time.time()
#         input_tensor, origin, spacing = preprocess_single(mhd_path)
#         logger.info(f"    ✓ Shape finale : {input_tensor.shape} ({time.time()-t1:.1f}s)")

#         logger.info("[3/5] Inference TiCNet CPU...")
#         t2 = time.time()
#         with torch.no_grad():
#             model.forward(input_tensor, [], [])
#         logger.info(f"    ✓ Inference terminée ({time.time()-t2:.1f}s)")

#         logger.info("[4/5] Extraction des détections...")
#         ensembles = model.ensemble_proposals.cpu().numpy()
#         logger.info(f"    ✓ {len(ensembles)} proposals total")

#         logger.info("[5/5] Filtrage nodules prob > 0.5...")
#         nodules = []
#         for det in ensembles:
#             score = float(det[1])
#             if score > 0.5:
#                 nodules.append({
#                     "z": float(det[2]),
#                     "y": float(det[3]),
#                     "x": float(det[4]),
#                     "diameter_mm": float(det[5]),
#                     "probability": score
#                 })

#         logger.info(f"    ✓ {len(nodules)} nodules détectés")
#         logger.info(f"TOTAL : {time.time()-t0:.1f}s")

#         return {
#             "status": "success",
#             "nodules_detected": len(nodules),
#             "nodules": nodules
#         }

#     except Exception as e:
#         import traceback
#         logger.error(f"ERREUR : {e}")
#         traceback.print_exc()
#         return {"error": str(e)}

#     finally:
#         shutil.rmtree(tmp_dir)


# @app.get("/health")
# def health():
#     return {"status": "ok", "model": "TiCNet", "device": "cpu"}
import os
import sys
import shutil
import tempfile
import time
import logging
import numpy as np
import torch
from skimage import measure
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, '/home/inas/STicnet')
os.environ['CUDA_VISIBLE_DEVICES'] = ''

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

from config import net_config
from net.main_net import build_model
from ticnet.utils.preprocess import (
    load_itk_image, HU2uint8, binarize, exclude_corner_middle,
    volume_filter, exclude_air, fill_hole, apply_mask, resample, get_lung_box
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# ── Charger le modèle une seule fois ─────────────────────────────────────────
logger.info("Loading model...")
model = build_model(net_config)
checkpoint = torch.load(
    '/home/inas/STicnet/results/ticnet/2_fold/model/120.pth',
    map_location='cpu'
)
model.load_state_dict(checkpoint['state_dict'])
model.cpu()
model.use_rcnn = True
model.set_mode('eval')
logger.info("Model loaded ✅")


def pad_to_factor(image, factor=16, pad_value=170):
    D, H, W = image.shape
    pad_D = (factor - D % factor) % factor
    pad_H = (factor - H % factor) % factor
    pad_W = (factor - W % factor) % factor
    return np.pad(image, ((0, pad_D), (0, pad_H), (0, pad_W)),
                  mode='constant', constant_values=pad_value)


def preprocess_no_mask(mhd_path, save_dir, pid):
    """Preprocessing exact sans masque pulmonaire"""
    logger.info(f"  Chargement {pid}...")
    img, origin, spacing = load_itk_image(mhd_path)
    logger.info(f"  Shape originale : {img.shape}, spacing : {spacing}")

    logger.info("  Binarisation...")
    binary_mask = binarize(img, spacing)
    label = measure.label(binary_mask, connectivity=1)
    label = exclude_corner_middle(label)
    label = volume_filter(label, spacing)
    binary_mask, has_lung = exclude_air(label, spacing)
    binary_mask = fill_hole(binary_mask)

    if not has_lung:
        logger.warning("  ⚠️ Poumons non détectés, masque complet utilisé")
        binary_mask1 = np.ones(img.shape, dtype=bool)
        binary_mask2 = np.zeros(img.shape, dtype=bool)
    else:
        logger.info("  ✅ Poumons détectés automatiquement")
        label = measure.label(binary_mask, connectivity=1)
        props = sorted(measure.regionprops(label),
                       key=lambda x: x.area, reverse=True)
        binary_mask1 = label == props[0].label
        binary_mask2 = (label == props[1].label
                        if len(props) > 1
                        else np.zeros_like(binary_mask1))

    img = HU2uint8(img)
    seg_img = apply_mask(img, binary_mask1, binary_mask2)

    logger.info("  Resampling (order=3)...")
    seg_img, _ = resample(seg_img, spacing, order=3)
    logger.info(f"  Shape après resample : {seg_img.shape}")

    lung_box = get_lung_box(binary_mask, seg_img.shape)
    z_min, z_max = lung_box[0]
    y_min, y_max = lung_box[1]
    x_min, x_max = lung_box[2]
    seg_img = seg_img[z_min:z_max, y_min:y_max, x_min:x_max]
    logger.info(f"  Shape après crop : {seg_img.shape}")

    ebox = np.array([z_min, y_min, x_min])

    np.save(os.path.join(save_dir, f'{pid}.npy'),         seg_img)
    np.save(os.path.join(save_dir, f'{pid}_origin.npy'),  origin)
    np.save(os.path.join(save_dir, f'{pid}_spacing.npy'), spacing)
    np.save(os.path.join(save_dir, f'{pid}_ebox.npy'),    ebox)

    return seg_img, origin, spacing, ebox


def run_inference(seg_img, origin, ebox):
    """Inference TiCNet + conversion coordonnées monde"""
    seg_img = pad_to_factor(seg_img, factor=16, pad_value=170)
    logger.info(f"  Shape après padding : {seg_img.shape}")

    seg_img = seg_img[np.newaxis, np.newaxis].astype(np.float32)
    seg_img = (seg_img - 128.0) / 128.0
    input_tensor = torch.from_numpy(seg_img)

    logger.info("  Inference TiCNet CPU...")
    t = time.time()
    with torch.no_grad():
        model.forward(input_tensor, [], [])
    logger.info(f"  Inference terminée ({time.time()-t:.1f}s)")

    ensembles = model.ensemble_proposals.cpu().numpy()
    logger.info(f"  {len(ensembles)} proposals total")

    nodules = []
    for det in ensembles:
        score = float(det[1])
        if score > 0.5:
            # voxel preprocessé → voxel resampleé
            vox_z = float(det[2]) + ebox[0]
            vox_y = float(det[3]) + ebox[1]
            vox_x = float(det[4]) + ebox[2]

            # voxel resampleé → coordonnées monde (new_spacing=1.0)
            world_z = origin[0] + vox_z * 1.0
            world_y = origin[1] + vox_y * 1.0
            world_x = origin[2] + vox_x * 1.0

            nodules.append({
                "voxel": {
                    "z": float(det[2]),
                    "y": float(det[3]),
                    "x": float(det[4]),
                },
                "world": {
                    "z": round(world_z, 2),
                    "y": round(world_y, 2),
                    "x": round(world_x, 2),
                },
                "diameter_mm": round(float(det[5]), 2),
                "probability":  round(score, 4),
            })

    logger.info(f"  {len(nodules)} nodules détectés (prob > 0.5)")
    return nodules


@app.post("/predict")
async def predict(
    mhd_file: UploadFile = File(...),
    raw_file:  UploadFile = File(...)
):
    tmp_dir  = tempfile.mkdtemp()
    save_dir = tempfile.mkdtemp()
    try:
        t0 = time.time()

        logger.info("[1/3] Réception des fichiers...")
        pid      = mhd_file.filename.replace('.mhd', '')
        mhd_path = os.path.join(tmp_dir, mhd_file.filename)
        raw_path = os.path.join(tmp_dir, raw_file.filename)

        with open(mhd_path, 'wb') as f:
            f.write(await mhd_file.read())
        with open(raw_path, 'wb') as f:
            f.write(await raw_file.read())
        logger.info(f"  ✓ Fichiers sauvegardés ({time.time()-t0:.1f}s)")

        logger.info("[2/3] Preprocessing...")
        t1 = time.time()
        seg_img, origin, spacing, ebox = preprocess_no_mask(
            mhd_path, save_dir, pid)
        logger.info(f"  ✓ Preprocessing terminé ({time.time()-t1:.1f}s)")

        logger.info("[3/3] Inference...")
        t2 = time.time()
        nodules = run_inference(seg_img, origin, ebox)
        logger.info(f"  ✓ Inference terminée ({time.time()-t2:.1f}s)")

        logger.info(f"TOTAL : {time.time()-t0:.1f}s")

        return {
            "status":           "success",
            "pid":              pid,
            "nodules_detected": len(nodules),
            "nodules":          nodules,
            "preprocessing": {
                "origin":  origin.tolist(),
                "spacing": spacing.tolist(),
                "ebox":    ebox.tolist(),
            }
        }

    except Exception as e:
        import traceback
        logger.error(f"ERREUR : {e}")
        traceback.print_exc()
        return {"error": str(e)}

    finally:
        shutil.rmtree(tmp_dir,  ignore_errors=True)
        shutil.rmtree(save_dir, ignore_errors=True)


@app.get("/health")
def health():
    return {"status": "ok", "model": "TiCNet", "device": "cpu"}