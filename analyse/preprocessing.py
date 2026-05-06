# # """
# # Preprocessing DICOM complet — identique à preprocess.py de TiCNet.
# # """

# # import numpy as np
# # import scipy.ndimage
# # import SimpleITK as sitk
# # import zipfile
# # import tempfile
# # import os
# # from skimage import measure, morphology


# # # ─────────────────────────────────────────────
# # # 1. LECTURE DICOM
# # # ─────────────────────────────────────────────

# # # def read_dicom_zip(zip_filepath: str):
# # #     with tempfile.TemporaryDirectory() as tmpdir:
# # #         with zipfile.ZipFile(zip_filepath, 'r') as zf:
# # #             zf.extractall(tmpdir)

# # #         dcm_files = []
# # #         for root, dirs, files in os.walk(tmpdir):
# # #             for f in files:
# # #                 fpath = os.path.join(root, f)
# # #                 if f.lower().endswith('.dcm') or _is_dicom(fpath):
# # #                     dcm_files.append(fpath)

# # #         if not dcm_files:
# # #             raise ValueError("Aucun fichier DICOM trouvé dans le ZIP.")

# # #         print(f"[Preprocess] {len(dcm_files)} fichiers DICOM trouvés.")
# # #         dicom_dir = os.path.dirname(dcm_files[0])

# # #         reader     = sitk.ImageSeriesReader()
# # #         series_ids = reader.GetGDCMSeriesIDs(dicom_dir)

# # #         if not series_ids:
# # #             raise ValueError("Aucune série DICOM valide trouvée.")

# # #         series_files = reader.GetGDCMSeriesFileNames(dicom_dir, series_ids[0])
# # #         reader.SetFileNames(series_files)
# # #         itk_img = reader.Execute()

# # #         volume  = sitk.GetArrayFromImage(itk_img).astype(np.float32)
# # #         spacing = np.array(list(reversed(itk_img.GetSpacing())))
# # #         origin  = np.array(list(reversed(itk_img.GetOrigin())))

# # #         print(f"[Preprocess] Volume HU : shape={volume.shape}, spacing={spacing}")
# # #         return volume, spacing, origin

# # def read_dicom_zip(zip_filepath: str):
# #     with tempfile.TemporaryDirectory() as tmpdir:
# #         with zipfile.ZipFile(zip_filepath, 'r') as zf:
# #             zf.extractall(tmpdir)

# #         dcm_files = []
# #         for root, dirs, files in os.walk(tmpdir):
# #             for f in files:
# #                 fpath = os.path.join(root, f)
# #                 if f.lower().endswith('.dcm') or _is_dicom(fpath):
# #                     dcm_files.append(fpath)

# #         if not dcm_files:
# #             raise ValueError("Aucun fichier DICOM trouvé dans le ZIP.")

# #         print(f"[Preprocess] {len(dcm_files)} fichiers DICOM trouvés.")
# #         dicom_dir = os.path.dirname(dcm_files[0])

# #         reader     = sitk.ImageSeriesReader()
# #         series_ids = reader.GetGDCMSeriesIDs(dicom_dir)

# #         if not series_ids:
# #             raise ValueError("Aucune série DICOM valide trouvée.")

# #         series_files = reader.GetGDCMSeriesFileNames(dicom_dir, series_ids[0])
# #         reader.SetFileNames(series_files)
# #         itk_img = reader.Execute()

# #         volume  = sitk.GetArrayFromImage(itk_img).astype(np.float32)
# #         spacing = np.array(list(reversed(itk_img.GetSpacing())))
# #         origin  = np.array(list(reversed(itk_img.GetOrigin())))

# #         # ← correction 4D
# #         if volume.ndim == 4:
# #             print(f"[Preprocess] Volume 4D détecté {volume.shape} → squeeze")
# #             volume  = volume[0]
# #             spacing = spacing[1:]
# #             origin  = origin[1:]

# #         print(f"[Preprocess] Volume HU : shape={volume.shape}, spacing={spacing}")
# #         return volume, spacing, origin
# # def _is_dicom(filepath: str) -> bool:
# #     try:
# #         with open(filepath, 'rb') as f:
# #             f.seek(128)
# #             return f.read(4) == b'DICM'
# #     except Exception:
# #         return False


# # # ─────────────────────────────────────────────
# # # 2. RESAMPLE À 1mm
# # # ─────────────────────────────────────────────

# # def resample(image: np.ndarray, spacing: np.ndarray, new_spacing=None) -> tuple:
# #     if new_spacing is None:
# #         new_spacing = np.array([1.0, 1.0, 1.0])

# #     new_shape       = np.round(np.array(image.shape) * spacing / new_spacing).astype(int)
# #     resize_factor   = new_shape / np.array(image.shape)
# #     image_resampled = scipy.ndimage.zoom(image, resize_factor, mode='nearest', order=1)
# #     actual_spacing  = spacing * np.array(image.shape) / new_shape

# #     print(f"[Preprocess] Resample : {image.shape} → {image_resampled.shape}")
# #     return image_resampled, actual_spacing


# # # ─────────────────────────────────────────────
# # # 3. HU → uint8
# # # ─────────────────────────────────────────────

# # def HU2uint8(image: np.ndarray, HU_min=-1200.0, HU_max=600.0, HU_nan=-2000.0) -> np.ndarray:
# #     image_new = np.array(image, dtype=np.float32)
# #     image_new[np.isnan(image_new)] = HU_nan
# #     image_new = (image_new - HU_min) / (HU_max - HU_min)
# #     image_new = np.clip(image_new, 0, 1)
# #     image_new = (image_new * 255).astype(np.uint8)
# #     return image_new


# # # ─────────────────────────────────────────────
# # # 4. EXTRACTION MASQUE PULMONAIRE
# # # ─────────────────────────────────────────────

# # def binarize(image: np.ndarray, spacing: np.ndarray,
# #              intensity_thred=-600, sigma=1.0,
# #              area_thred=30.0, eccen_thred=0.99, corner_side=10) -> np.ndarray:
# #     binary_mask = np.zeros(image.shape, dtype=bool)
# #     side_len    = image.shape[1]
# #     grid_axis   = np.linspace(-side_len / 2 + 0.5, side_len / 2 - 0.5, side_len)
# #     x, y        = np.meshgrid(grid_axis, grid_axis)
# #     distance    = np.sqrt(np.square(x) + np.square(y))
# #     nan_mask    = (distance < side_len / 2).astype(float)
# #     nan_mask[nan_mask == 0] = np.nan

# #     for i in range(image.shape[0]):
# #         slice_raw = np.array(image[i]).astype('float32')
# #         num_uniq  = len(np.unique(slice_raw[0:corner_side, 0:corner_side]))
# #         if num_uniq == 1:
# #             slice_raw *= nan_mask

# #         slice_smoothed = scipy.ndimage.gaussian_filter(slice_raw, sigma, truncate=2.0)
# #         slice_binary   = slice_smoothed < intensity_thred
# #         label          = measure.label(slice_binary)
# #         properties     = measure.regionprops(label)
# #         label_valid    = set()

# #         for prop in properties:
# #             area_mm = prop.area * spacing[1] * spacing[2]
# #             if area_mm > area_thred and prop.eccentricity < eccen_thred:
# #                 label_valid.add(prop.label)

# #         slice_binary   =np.isin(label, list(label_valid)).reshape(label.shape)
# #         binary_mask[i] = slice_binary

# #     return binary_mask


# # def volume_filter(label: np.ndarray, spacing: np.ndarray,
# #                   vol_min=0.2, vol_max=8.2) -> np.ndarray:
# #     properties = measure.regionprops(label)
# #     for prop in properties:
# #         vol = prop.area * spacing.prod()
# #         if vol < vol_min * 1e6 or vol > vol_max * 1e6:
# #             label[label == prop.label] = 0
# #     return label


# # def exclude_corner_middle(label: np.ndarray) -> np.ndarray:
# #     mid = int(label.shape[2] / 2)
# #     corner_label = set([
# #         label[0, 0, 0],   label[0, 0, -1],
# #         label[0, -1, 0],  label[0, -1, -1],
# #         label[-1, 0, 0],  label[-1, 0, -1],
# #         label[-1, -1, 0], label[-1, -1, -1],
# #     ])
# #     middle_label = set([
# #         label[0, 0, mid],  label[0, -1, mid],
# #         label[-1, 0, mid], label[-1, -1, mid],
# #     ])
# #     for l in corner_label:
# #         label[label == l] = 0
# #     for l in middle_label:
# #         label[label == l] = 0
# #     return label


# # def fill_hole(binary_mask: np.ndarray) -> np.ndarray:
# #     label = measure.label(~binary_mask)
# #     corner_label = set([
# #         label[0, 0, 0],   label[0, 0, -1],
# #         label[0, -1, 0],  label[0, -1, -1],
# #         label[-1, 0, 0],  label[-1, 0, -1],
# #         label[-1, -1, 0], label[-1, -1, -1],
# #     ])
# #     binary_mask = ~np.in1d(label, list(corner_label)).reshape(label.shape)
# #     return binary_mask


# # def exclude_air(label: np.ndarray, spacing: np.ndarray,
# #                 area_thred=3e3, dist_thred=62) -> tuple:
# #     y_axis   = np.linspace(-label.shape[1]/2+0.5, label.shape[1]/2-0.5, label.shape[1]) * spacing[1]
# #     x_axis   = np.linspace(-label.shape[2]/2+0.5, label.shape[2]/2-0.5, label.shape[2]) * spacing[2]
# #     y, x     = np.meshgrid(y_axis, x_axis)
# #     distance = np.sqrt(np.square(y) + np.square(x))
# #     dist_max = np.max(distance)

# #     vols        = measure.regionprops(label)
# #     label_valid = set()

# #     for vol in vols:
# #         single_vol   = (label == vol.label)
# #         slice_area   = np.zeros(label.shape[0])
# #         min_distance = np.zeros(label.shape[0])

# #         for i in range(label.shape[0]):
# #             slice_area[i]   = np.sum(single_vol[i]) * np.prod(spacing[1:3])
# #             min_distance[i] = np.min(single_vol[i] * distance +
# #                                      (1 - single_vol[i]) * dist_max)

# #         valid_slices = [min_distance[i] for i in range(label.shape[0])
# #                         if slice_area[i] > area_thred]
# #         if valid_slices and np.average(valid_slices) < dist_thred:
# #             label_valid.add(vol.label)

# #     binary_mask =np.isin(label, list(label_valid)).reshape(label.shape)
# #     has_lung    = len(label_valid) > 0
# #     return binary_mask, has_lung


# # def convex_hull_dilate(binary_mask: np.ndarray,
# #                        dilate_factor=1.5, iterations=10) -> np.ndarray:
# #     binary_mask_dilated = np.array(binary_mask)
# #     for i in range(binary_mask.shape[0]):
# #         slice_binary = binary_mask[i]
# #         if np.sum(slice_binary) > 0:
# #             slice_convex = morphology.convex_hull_image(slice_binary)
# #             if np.sum(slice_convex) <= dilate_factor * np.sum(slice_binary):
# #                 binary_mask_dilated[i] = slice_convex

# #     struct = scipy.ndimage.generate_binary_structure(3, 1)
# #     binary_mask_dilated = scipy.ndimage.binary_dilation(
# #         binary_mask_dilated, structure=struct, iterations=iterations)
# #     return binary_mask_dilated


# # def extract_lung(image: np.ndarray, spacing: np.ndarray) -> np.ndarray:
# #     print("[Preprocess] Extraction masque pulmonaire...")
# #     binary_mask           = binarize(image, spacing)
# #     label                 = measure.label(binary_mask, connectivity=1)
# #     label                 = exclude_corner_middle(label)
# #     label                 = volume_filter(label, spacing)
# #     binary_mask, has_lung = exclude_air(label, spacing)
# #     binary_mask           = fill_hole(binary_mask)
# #     print(f"[Preprocess] Masque pulmonaire : has_lung={has_lung}")
# #     return binary_mask


# # # ─────────────────────────────────────────────
# # # 5. APPLY MASK
# # # ─────────────────────────────────────────────

# # def apply_mask(image: np.ndarray, binary_mask: np.ndarray, pad_value=170) -> np.ndarray:
# #     mid              = image.shape[2] // 2
# #     binary_mask1     = np.array(binary_mask)
# #     binary_mask2     = np.array(binary_mask)
# #     binary_mask1[:, :, mid:] = False
# #     binary_mask2[:, :, :mid] = False

# #     binary_mask1_dilated = convex_hull_dilate(binary_mask1)
# #     binary_mask2_dilated = convex_hull_dilate(binary_mask2)
# #     binary_mask_dilated  = binary_mask1_dilated | binary_mask2_dilated

# #     image_new = (image * binary_mask_dilated +
# #                  pad_value * (~binary_mask_dilated).astype(np.uint8))
# #     return image_new.astype(np.uint8)


# # # ─────────────────────────────────────────────
# # # 6. CROP AUTOUR DU POUMON
# # # ─────────────────────────────────────────────

# # def get_lung_box(binary_mask: np.ndarray, new_shape: np.ndarray, margin=5) -> np.ndarray:
# #     # Force 3D
# #     if binary_mask.ndim == 4:
# #         binary_mask = binary_mask[0]

# #     z_true, y_true, x_true = np.where(binary_mask)

# #     # Aucun poumon trouvé → retourne volume entier
# #     if len(z_true) == 0:
# #         return np.array([
# #             [0, new_shape[0]],
# #             [0, new_shape[1]],
# #             [0, new_shape[2]],
# #         ])

# #     old_shape = np.array(binary_mask.shape[:3], dtype=np.float64)  # ← force 3D
# #     new_shape = np.array(new_shape[:3],         dtype=np.float64)  # ← force 3D

# #     lung_box = np.array([
# #         [np.min(z_true), np.max(z_true)],
# #         [np.min(y_true), np.max(y_true)],
# #         [np.min(x_true), np.max(x_true)],
# #     ], dtype=np.float64)

# #     lung_box = lung_box * np.expand_dims(new_shape, 1) / np.expand_dims(old_shape, 1)
# #     lung_box = np.floor(lung_box).astype(int)

# #     lung_box[0] = (max(0, lung_box[0, 0] - margin),
# #                    min(int(new_shape[0]), lung_box[0, 1] + margin))
# #     lung_box[1] = (max(0, lung_box[1, 0] - margin),
# #                    min(int(new_shape[1]), lung_box[1, 1] + margin))
# #     lung_box[2] = (max(0, lung_box[2, 0] - margin),
# #                    min(int(new_shape[2]), lung_box[2, 1] + margin))

# #     return lung_box


# # # ─────────────────────────────────────────────
# # # 7. PIPELINE COMPLET
# # # ─────────────────────────────────────────────

# # def preprocess_dicom_zip(zip_filepath: str) -> np.ndarray:
# #     """
# #     Pipeline complet DICOM ZIP → volume préprocessé prêt pour TiCNet.
# #     Retourne un array float32 [Z, Y, X] avec pad_value=170.
# #     """
# #     # 1. Lit le DICOM
# #     volume_hu, spacing, origin = read_dicom_zip(zip_filepath)

# #     # 2. Resample à 1mm
# #     volume_resampled, new_spacing = resample(volume_hu, spacing)

# #     # 3. HU → uint8
# #     volume_uint8 = HU2uint8(volume_resampled)
# #     print(f"[Preprocess] uint8 : min={volume_uint8.min()}, max={volume_uint8.max()}")

# #     # 4. Extraction masque pulmonaire
# #     try:
# #         binary_mask = extract_lung(volume_resampled, new_spacing)
# #     except Exception as e:
# #         print(f"[Preprocess] Avertissement masque : {e}")
# #         print("[Preprocess] Utilisation du volume sans masque.")
# #         return volume_uint8.astype(np.float32)

# #     # 5. Apply mask
# #     try:
# #         volume_masked = apply_mask(volume_uint8, binary_mask, pad_value=170)
# #     except Exception as e:
# #         print(f"[Preprocess] Avertissement apply_mask : {e}")
# #         volume_masked = volume_uint8

# #     # 6. Crop autour du poumon
# #     try:
# #         lung_box = get_lung_box(
# #             binary_mask,
# #             np.array(volume_masked.shape[:3])  # ← force 3D ici
# #         )
# #         z_min, z_max = lung_box[0]
# #         y_min, y_max = lung_box[1]
# #         x_min, x_max = lung_box[2]
# #         volume_cropped = volume_masked[z_min:z_max, y_min:y_max, x_min:x_max]
# #         print(f"[Preprocess] Crop : {volume_masked.shape} → {volume_cropped.shape}")
# #     except Exception as e:
# #         print(f"[Preprocess] Avertissement crop : {e}")
# #         volume_cropped = volume_masked  # ← dans le except uniquement

# #     return volume_cropped.astype(np.float32)
# """
# Preprocessing DICOM complet — identique à preprocess.py de TiCNet.
# Pipeline :
#   1. Lit la série DICOM → volume HU + spacing + origin
#   2. HU2uint8 : clip(-1200, 600) → [0, 255]   ← ORDRE CORRIGÉ : uint8 AVANT resample
#   3. Resample à 1mm/voxel                       ← order=3 pour matcher l'entraînement
#   4. Extraction masque pulmonaire (binarize + connected components)
#   5. apply_mask avec pad_value=170              ← split gauche/droite par composantes connexes
#   6. Crop autour du poumon
#   7. Sauvegarde les 4 fichiers sur disque       ← _seg.nrrd + _origin.npy + _spacing.npy + _ebox.npy
#   8. Retourne un array uint8 [Z, Y, X]          ← uint8, PAS float32

# FIXES APPLIQUÉS (v2) :
#   ✅ FIX CRITIQUE 2  : GetGDCMSeriesIDs cherche dans le dossier le plus profond
#                        contenant des .dcm (robustesse aux ZIP avec sous-dossiers)
#   ✅ FIX CRITIQUE 1  : le masque binaire extrait sur volume HU est redimensionné
#                        pour correspondre exactement à la shape du volume uint8
#                        resampleé (évite décalage de 1 pixel entre order=1 et order=3)
#   ✅ FIX IMPORTANT 4 : ebox sauvegardé comme [[zmin,zmax],[ymin,ymax],[xmin,xmax]]
#                        (format complet attendu par BboxReader)
#   ✅ FIX IMPORTANT 5 : origin mis à jour après crop pour refléter le décalage de
#                        coordonnées introduit par le crop
# """

# import numpy as np
# import scipy.ndimage
# import SimpleITK as sitk
# import zipfile
# import tempfile
# import os
# import nrrd
# from skimage import measure, morphology


# # ─────────────────────────────────────────────────────
# # 1. LECTURE DICOM
# # ─────────────────────────────────────────────────────

# def read_dicom_zip(zip_filepath: str):
#     """
#     Lit un ZIP contenant des fichiers DICOM.
#     Retourne (volume_HU, spacing_ZYX, origin_ZYX)

#     ✅ FIX CRITIQUE 2 : cherche le dossier le plus profond contenant des .dcm
#     pour que GetGDCMSeriesIDs trouve la série même dans des ZIP avec sous-dossiers
#     (ex: patient_001/series1/*.dcm).
#     """
#     with tempfile.TemporaryDirectory() as tmpdir:
#         with zipfile.ZipFile(zip_filepath, 'r') as zf:
#             zf.extractall(tmpdir)

#         # Cherche les fichiers DICOM récursivement
#         dcm_files = []
#         for root, dirs, files in os.walk(tmpdir):
#             for f in files:
#                 fpath = os.path.join(root, f)
#                 if f.lower().endswith('.dcm') or _is_dicom(fpath):
#                     dcm_files.append(fpath)

#         if not dcm_files:
#             raise ValueError("Aucun fichier DICOM trouvé dans le ZIP.")

#         print(f"[Preprocess] {len(dcm_files)} fichiers DICOM trouvés.")

#         # ✅ FIX CRITIQUE 2 : trouve le dossier contenant le plus de .dcm
#         # (robuste aux structures ZIP avec sous-dossiers multiples)
#         dcm_dirs = set(os.path.dirname(f) for f in dcm_files)
#         best_dir = max(dcm_dirs, key=lambda d: sum(1 for f in dcm_files if os.path.dirname(f) == d))
#         print(f"[Preprocess] Dossier série DICOM sélectionné : {best_dir}")

#         reader     = sitk.ImageSeriesReader()
#         series_ids = reader.GetGDCMSeriesIDs(best_dir)

#         if not series_ids:
#             raise ValueError(f"Aucune série DICOM valide trouvée dans {best_dir}.")

#         series_files = reader.GetGDCMSeriesFileNames(best_dir, series_ids[0])
#         reader.SetFileNames(series_files)
#         itk_img = reader.Execute()

#         volume  = sitk.GetArrayFromImage(itk_img).astype(np.float32)  # [Z, Y, X] HU
#         spacing = np.array(list(reversed(itk_img.GetSpacing())))       # [Z, Y, X] mm
#         origin  = np.array(list(reversed(itk_img.GetOrigin())))        # [Z, Y, X]

#         # Gestion volume 4D (certains DICOM multi-phase)
#         if volume.ndim == 4:
#             volume  = volume[0]
#             spacing = spacing[1:]
#             print(f"[Preprocess] Volume 4D détecté → squeeze dim 0")

#         print(f"[Preprocess] Volume HU : shape={volume.shape}, spacing={spacing}")
#         return volume, spacing, origin


# def _is_dicom(filepath: str) -> bool:
#     try:
#         with open(filepath, 'rb') as f:
#             f.seek(128)
#             return f.read(4) == b'DICM'
#     except Exception:
#         return False


# # ─────────────────────────────────────────────────────
# # 2. HU → uint8  (AVANT resample, comme TiCNet preprocess.py)
# # ─────────────────────────────────────────────────────

# def HU2uint8(image: np.ndarray, HU_min=-1200.0, HU_max=600.0, HU_nan=-2000.0) -> np.ndarray:
#     """
#     Convertit les valeurs HU en uint8 [0, 255].
#     Identique à HU2uint8() dans preprocess.py TiCNet.
#     Appelé AVANT resample() pour aligner sur l'ordre TiCNet.
#     """
#     image_new = np.array(image, dtype=np.float32)
#     image_new[np.isnan(image_new)] = HU_nan

#     image_new = (image_new - HU_min) / (HU_max - HU_min)
#     image_new = np.clip(image_new, 0, 1)
#     image_new = (image_new * 255).astype(np.uint8)

#     return image_new


# # ─────────────────────────────────────────────────────
# # 3. RESAMPLE À 1mm  (order=3 pour matcher l'entraînement)
# # ─────────────────────────────────────────────────────

# def resample(image: np.ndarray, spacing: np.ndarray, new_spacing=None, order=3) -> tuple:
#     """
#     Resample le volume CT vers new_spacing (défaut 1x1x1 mm).
#     Identique à resample() dans preprocess.py TiCNet.
#     order=3 (cubique) pour le volume principal, order=1 pour le masque.
#     """
#     if new_spacing is None:
#         new_spacing = np.array([1.0, 1.0, 1.0])

#     new_shape       = np.round(np.array(image.shape) * spacing / new_spacing).astype(int)
#     resize_factor   = new_shape / np.array(image.shape)
#     image_resampled = scipy.ndimage.zoom(image, resize_factor, mode='nearest', order=order)
#     actual_spacing  = spacing * np.array(image.shape) / new_shape

#     print(f"[Preprocess] Resample : {image.shape} → {image_resampled.shape}")
#     return image_resampled, actual_spacing


# # ─────────────────────────────────────────────────────
# # 4. EXTRACTION MASQUE PULMONAIRE
# # ─────────────────────────────────────────────────────

# def binarize(image: np.ndarray, spacing: np.ndarray,
#              intensity_thred=-600, sigma=1.0,
#              area_thred=30.0, eccen_thred=0.99, corner_side=10) -> np.ndarray:
#     """
#     Binarise le volume CT slice par slice pour isoler les poumons.
#     Identique à binarize() dans preprocess.py TiCNet.
#     Note: reçoit le volume HU (float32), pas uint8.
#     """
#     binary_mask = np.zeros(image.shape, dtype=bool)
#     side_len    = image.shape[1]
#     grid_axis   = np.linspace(-side_len / 2 + 0.5, side_len / 2 - 0.5, side_len)
#     x, y        = np.meshgrid(grid_axis, grid_axis)
#     distance    = np.sqrt(np.square(x) + np.square(y))
#     nan_mask    = (distance < side_len / 2).astype(float)
#     nan_mask[nan_mask == 0] = np.nan

#     for i in range(image.shape[0]):
#         slice_raw = np.array(image[i]).astype('float32')
#         num_uniq  = len(np.unique(slice_raw[0:corner_side, 0:corner_side]))
#         if num_uniq == 1:
#             slice_raw *= nan_mask

#         slice_smoothed = scipy.ndimage.gaussian_filter(slice_raw, sigma, truncate=2.0)
#         slice_binary   = slice_smoothed < intensity_thred
#         label          = measure.label(slice_binary)
#         properties     = measure.regionprops(label)
#         label_valid    = set()

#         for prop in properties:
#             area_mm = prop.area * spacing[1] * spacing[2]
#             if area_mm > area_thred and prop.eccentricity < eccen_thred:
#                 label_valid.add(prop.label)

#         slice_binary   = np.isin(label, list(label_valid)).reshape(label.shape)
#         binary_mask[i] = slice_binary

#     return binary_mask


# def volume_filter(label: np.ndarray, spacing: np.ndarray,
#                   vol_min=0.2, vol_max=8.2) -> np.ndarray:
#     properties = measure.regionprops(label)
#     for prop in properties:
#         vol = prop.area * spacing.prod()
#         if vol < vol_min * 1e6 or vol > vol_max * 1e6:
#             label[label == prop.label] = 0
#     return label


# def exclude_corner_middle(label: np.ndarray) -> np.ndarray:
#     mid = int(label.shape[2] / 2)
#     corner_label = set([
#         label[0, 0, 0],   label[0, 0, -1],
#         label[0, -1, 0],  label[0, -1, -1],
#         label[-1, 0, 0],  label[-1, 0, -1],
#         label[-1, -1, 0], label[-1, -1, -1],
#     ])
#     middle_label = set([
#         label[0, 0, mid],  label[0, -1, mid],
#         label[-1, 0, mid], label[-1, -1, mid],
#     ])
#     for l in corner_label:
#         label[label == l] = 0
#     for l in middle_label:
#         label[label == l] = 0
#     return label


# def fill_hole(binary_mask: np.ndarray) -> np.ndarray:
#     label = measure.label(~binary_mask)
#     corner_label = set([
#         label[0, 0, 0],   label[0, 0, -1],
#         label[0, -1, 0],  label[0, -1, -1],
#         label[-1, 0, 0],  label[-1, 0, -1],
#         label[-1, -1, 0], label[-1, -1, -1],
#     ])
#     binary_mask = ~np.isin(label, list(corner_label)).reshape(label.shape)
#     return binary_mask


# def exclude_air(label: np.ndarray, spacing: np.ndarray,
#                 area_thred=3e3, dist_thred=62) -> tuple:
#     y_axis   = np.linspace(-label.shape[1]/2+0.5, label.shape[1]/2-0.5, label.shape[1]) * spacing[1]
#     x_axis   = np.linspace(-label.shape[2]/2+0.5, label.shape[2]/2-0.5, label.shape[2]) * spacing[2]
#     y, x     = np.meshgrid(y_axis, x_axis)
#     distance = np.sqrt(np.square(y) + np.square(x))
#     dist_max = np.max(distance)

#     vols        = measure.regionprops(label)
#     label_valid = set()

#     for vol in vols:
#         single_vol   = (label == vol.label)
#         slice_area   = np.zeros(label.shape[0])
#         min_distance = np.zeros(label.shape[0])

#         for i in range(label.shape[0]):
#             slice_area[i]   = np.sum(single_vol[i]) * np.prod(spacing[1:3])
#             min_distance[i] = np.min(single_vol[i] * distance +
#                                      (1 - single_vol[i]) * dist_max)

#         valid_slices = [min_distance[i] for i in range(label.shape[0])
#                         if slice_area[i] > area_thred]
#         if valid_slices and np.average(valid_slices) < dist_thred:
#             label_valid.add(vol.label)

#     binary_mask = np.isin(label, list(label_valid)).reshape(label.shape)
#     has_lung    = len(label_valid) > 0
#     return binary_mask, has_lung


# def convex_hull_dilate(binary_mask: np.ndarray,
#                        dilate_factor=1.5, iterations=10) -> np.ndarray:
#     binary_mask_dilated = np.array(binary_mask)
#     for i in range(binary_mask.shape[0]):
#         slice_binary = binary_mask[i]
#         if np.sum(slice_binary) > 0:
#             slice_convex = morphology.convex_hull_image(slice_binary)
#             if np.sum(slice_convex) <= dilate_factor * np.sum(slice_binary):
#                 binary_mask_dilated[i] = slice_convex

#     struct = scipy.ndimage.generate_binary_structure(3, 1)
#     binary_mask_dilated = scipy.ndimage.binary_dilation(
#         binary_mask_dilated, structure=struct, iterations=iterations)
#     return binary_mask_dilated


# def extract_lung(image: np.ndarray, spacing: np.ndarray) -> np.ndarray:
#     """
#     Extrait le masque pulmonaire complet.
#     Identique à extract_lung() dans preprocess.py TiCNet.
#     Reçoit le volume HU brut (avant uint8) pour que le seuil -600 HU soit valide.
#     """
#     print("[Preprocess] Extraction masque pulmonaire...")
#     binary_mask           = binarize(image, spacing)
#     label                 = measure.label(binary_mask, connectivity=1)
#     label                 = exclude_corner_middle(label)
#     label                 = volume_filter(label, spacing)
#     binary_mask, has_lung = exclude_air(label, spacing)
#     binary_mask           = fill_hole(binary_mask)
#     print(f"[Preprocess] Masque pulmonaire : has_lung={has_lung}")
#     return binary_mask


# # ─────────────────────────────────────────────────────
# # 5. APPLY MASK
# #    Split gauche/droite par composantes connexes
# # ─────────────────────────────────────────────────────

# def apply_mask(image: np.ndarray, binary_mask: np.ndarray, pad_value=170) -> np.ndarray:
#     """
#     Applique le masque pulmonaire — zones hors poumon → pad_value.
#     Identifie les 2 poumons via les 2 plus grandes composantes connexes
#     (robuste à l'asymétrie anatomique), au lieu de couper au milieu X.
#     """
#     label = measure.label(binary_mask)
#     props = measure.regionprops(label)

#     if len(props) == 0:
#         return (image * binary_mask + pad_value * (~binary_mask).astype(np.uint8)).astype(np.uint8)

#     # Trie par volume décroissant, garde les 2 plus grandes
#     props_sorted = sorted(props, key=lambda p: p.area, reverse=True)[:2]

#     binary_mask1 = (label == props_sorted[0].label)
#     if len(props_sorted) > 1:
#         binary_mask2 = (label == props_sorted[1].label)
#     else:
#         binary_mask2 = np.zeros_like(binary_mask1)

#     binary_mask1_dilated = convex_hull_dilate(binary_mask1)
#     binary_mask2_dilated = convex_hull_dilate(binary_mask2)
#     binary_mask_dilated  = binary_mask1_dilated | binary_mask2_dilated

#     image_new = (image * binary_mask_dilated +
#                  pad_value * (~binary_mask_dilated).astype(np.uint8))
#     return image_new.astype(np.uint8)


# # ─────────────────────────────────────────────────────
# # 6. CROP AUTOUR DU POUMON
# # ─────────────────────────────────────────────────────

# def get_lung_box(binary_mask: np.ndarray, new_shape: np.ndarray, margin=5) -> np.ndarray:
#     # Force 3D
#     if binary_mask.ndim == 4:
#         binary_mask = binary_mask[0]

#     z_true, y_true, x_true = np.where(binary_mask)

#     # Aucun poumon trouvé → retourne volume entier
#     if len(z_true) == 0:
#         return np.array([
#             [0, new_shape[0]],
#             [0, new_shape[1]],
#             [0, new_shape[2]],
#         ])

#     old_shape = np.array(binary_mask.shape[:3], dtype=np.float64)
#     new_shape = np.array(new_shape[:3],         dtype=np.float64)

#     lung_box = np.array([
#         [np.min(z_true), np.max(z_true)],
#         [np.min(y_true), np.max(y_true)],
#         [np.min(x_true), np.max(x_true)],
#     ], dtype=np.float64)

#     lung_box = lung_box * np.expand_dims(new_shape, 1) / np.expand_dims(old_shape, 1)
#     lung_box = np.floor(lung_box).astype(int)

#     lung_box[0] = (max(0, lung_box[0, 0] - margin),
#                    min(int(new_shape[0]), lung_box[0, 1] + margin))
#     lung_box[1] = (max(0, lung_box[1, 0] - margin),
#                    min(int(new_shape[1]), lung_box[1, 1] + margin))
#     lung_box[2] = (max(0, lung_box[2, 0] - margin),
#                    min(int(new_shape[2]), lung_box[2, 1] + margin))

#     return lung_box


# # ─────────────────────────────────────────────────────
# # 7. PIPELINE COMPLET
# # ─────────────────────────────────────────────────────

# def preprocess_dicom_zip(zip_filepath: str, save_dir: str = None, pid: str = None) -> np.ndarray:
#     """
#     Pipeline complet DICOM ZIP → volume préprocessé prêt pour TiCNet.

#     Retourne un array uint8 [Z, Y, X] avec pad_value=170.

#     Fichiers sauvegardés si save_dir + pid fournis :
#         {pid}_seg.nrrd      ← volume préprocessé (lu par BboxReader)
#         {pid}_origin.npy    ← origine spatiale MISE À JOUR après crop
#         {pid}_spacing.npy   ← spacing après resample
#         {pid}_ebox.npy      ← bounding box complète [[zmin,zmax],[ymin,ymax],[xmin,xmax]]

#     FIXES v2 appliqués :
#         ✅ CRITIQUE 2 : GetGDCMSeriesIDs sur le meilleur sous-dossier (ZIP avec subdirs)
#         ✅ CRITIQUE 1 : masque redimensionné pour matcher la shape du volume uint8
#         ✅ IMPORTANT 4 : ebox format [[min,max],...] complet (pas seulement min corner)
#         ✅ IMPORTANT 5 : origin ajusté par le crop offset en mm
#     """
#     # 1. Lit le DICOM
#     volume_hu, spacing, origin = read_dicom_zip(zip_filepath)

#     # 2. HU → uint8 EN PREMIER (avant resample, ordre aligné sur TiCNet)
#     volume_uint8 = HU2uint8(volume_hu)
#     print(f"[Preprocess] uint8 avant resample : min={volume_uint8.min()}, max={volume_uint8.max()}")

#     # 3. Resample à 1mm (order=3 pour matcher l'entraînement)
#     volume_resampled, new_spacing = resample(volume_uint8.astype(np.float32), spacing, order=3)
#     volume_resampled = np.clip(volume_resampled, 0, 255).astype(np.uint8)
#     print(f"[Preprocess] Après resample uint8 : min={volume_resampled.min()}, max={volume_resampled.max()}")

#     # 4. Extraction masque pulmonaire sur HU brut (seuil -600 HU doit être en HU)
#     binary_mask = None
#     try:
#         # Resample le volume HU avec order=1 (suffisant pour le masque)
#         volume_hu_resampled, _ = resample(volume_hu, spacing, order=1)

#         # ✅ FIX CRITIQUE 1 : les deux resamples (order=1 et order=3) peuvent produire
#         # des shapes légèrement différentes (±1 pixel par axe à cause des arrondis).
#         # On force le masque à avoir exactement la même shape que volume_resampled.
#         if volume_hu_resampled.shape != volume_resampled.shape:
#             zoom_factors = np.array(volume_resampled.shape) / np.array(volume_hu_resampled.shape)
#             print(f"[Preprocess] Ajustement shape masque HU : "
#                   f"{volume_hu_resampled.shape} → {volume_resampled.shape}")
#             volume_hu_resampled = scipy.ndimage.zoom(
#                 volume_hu_resampled, zoom_factors, mode='nearest', order=1)

#         binary_mask = extract_lung(volume_hu_resampled, new_spacing)

#         # ✅ FIX CRITIQUE 1 (suite) : redimensionne le masque binaire si nécessaire
#         # pour correspondre exactement à volume_resampled
#         if binary_mask.shape != volume_resampled.shape:
#             zoom_factors = np.array(volume_resampled.shape) / np.array(binary_mask.shape)
#             print(f"[Preprocess] Redimensionnement masque binaire : "
#                   f"{binary_mask.shape} → {volume_resampled.shape}")
#             binary_mask = scipy.ndimage.zoom(
#                 binary_mask.astype(np.float32),
#                 zoom_factors,
#                 order=0   # nearest neighbor pour un masque binaire
#             ).astype(bool)

#     except Exception as e:
#         print(f"[Preprocess] Avertissement extraction masque : {e}")
#         print("[Preprocess] Utilisation du volume sans masque.")

#     if binary_mask is not None:
#         # 5. Apply mask (split par composantes connexes)
#         try:
#             volume_masked = apply_mask(volume_resampled, binary_mask, pad_value=170)
#         except Exception as e:
#             print(f"[Preprocess] Avertissement apply_mask : {e}")
#             volume_masked = volume_resampled

#         # 6. Crop autour du poumon
#         try:
#             lung_box = get_lung_box(
#                 binary_mask,
#                 np.array(volume_masked.shape[:3])
#             )
#             z_min, z_max = lung_box[0]
#             y_min, y_max = lung_box[1]
#             x_min, x_max = lung_box[2]
#             volume_cropped = volume_masked[z_min:z_max, y_min:y_max, x_min:x_max]
#             print(f"[Preprocess] Crop poumon : {volume_masked.shape} → {volume_cropped.shape}")

#             # ✅ FIX IMPORTANT 4 : ebox format complet [[min,max],...] attendu par BboxReader
#             ebox = np.array([
#                 [z_min, z_max],
#                 [y_min, y_max],
#                 [x_min, x_max],
#             ])

#             # ✅ FIX IMPORTANT 5 : met à jour l'origin pour refléter le décalage du crop
#             # crop_offset_mm = coin min du crop, converti en mm via new_spacing
#             crop_offset_mm = np.array([z_min, y_min, x_min], dtype=np.float64) * new_spacing
#             origin_final   = origin + crop_offset_mm
#             print(f"[Preprocess] Origin ajustée après crop : {origin} → {origin_final}")

#         except Exception as e:
#             print(f"[Preprocess] Avertissement crop : {e}")
#             volume_cropped = volume_masked
#             ebox           = np.array([[0, volume_masked.shape[0]],
#                                        [0, volume_masked.shape[1]],
#                                        [0, volume_masked.shape[2]]])
#             origin_final   = origin
#     else:
#         volume_cropped = volume_resampled
#         ebox           = np.array([[0, volume_resampled.shape[0]],
#                                    [0, volume_resampled.shape[1]],
#                                    [0, volume_resampled.shape[2]]])
#         origin_final   = origin

#     # Retourne uint8 — BboxReader lit le _seg.nrrd en uint8 et applique (x-128)/128
#     volume_final = volume_cropped.astype(np.uint8)

#     # Sauvegarde les 4 fichiers sur disque
#     if save_dir is not None and pid is not None:
#         os.makedirs(save_dir, exist_ok=True)

#         # Fichier principal — lu par BboxReader en mode eval
#         nrrd.write(os.path.join(save_dir, f'{pid}_seg.nrrd'), volume_final)

#         # ✅ FIX IMPORTANT 5 : origin_final (ajustée après crop), pas origin brute
#         np.save(os.path.join(save_dir, f'{pid}_origin.npy'),  origin_final)
#         np.save(os.path.join(save_dir, f'{pid}_spacing.npy'), new_spacing)

#         # ✅ FIX IMPORTANT 4 : ebox format [[zmin,zmax],[ymin,ymax],[xmin,xmax]]
#         np.save(os.path.join(save_dir, f'{pid}_ebox.npy'),    ebox)

#         print(f"[Preprocess] Fichiers sauvegardés dans {save_dir}/")
#         print(f"  → {pid}_seg.nrrd   shape={volume_final.shape}")
#         print(f"  → {pid}_origin.npy  {origin_final}")
#         print(f"  → {pid}_spacing.npy {new_spacing}")
#         print(f"  → {pid}_ebox.npy    {ebox}")

#     return volume_final

"""
Preprocessing DICOM complet — identique à preprocess.py de TiCNet.
Pipeline :
  1. Lit la série DICOM → volume HU + spacing + origin
  2. HU2uint8 : clip(-1200, 600) → [0, 255]   ← ORDRE CORRIGÉ : uint8 AVANT resample
  3. Resample à 1mm/voxel                       ← order=3 pour matcher l'entraînement
  4. Extraction masque pulmonaire (binarize + connected components)
  5. apply_mask avec pad_value=170              ← split gauche/droite par composantes connexes
  6. Crop autour du poumon
  7. Sauvegarde les 4 fichiers sur disque       ← _seg.nrrd + _origin.npy + _spacing.npy + _ebox.npy
  8. Retourne un array uint8 [Z, Y, X]          ← uint8, PAS float32
"""

import numpy as np
import scipy.ndimage
import SimpleITK as sitk
import zipfile
import tempfile
import os
import nrrd
from skimage import measure, morphology


# ─────────────────────────────────────────────────────
# 1. LECTURE DICOM
# ─────────────────────────────────────────────────────

# def read_dicom_zip(zip_filepath: str):
#     """
#     Lit un ZIP contenant des fichiers DICOM.
#     Retourne (volume_HU, spacing_ZYX, origin_ZYX)

#     FIX CRITIQUE 3 : utilise tmpdir directement dans GetGDCMSeriesIDs
#     pour couvrir tous les sous-dossiers du ZIP.
#     """
#     with tempfile.TemporaryDirectory() as tmpdir:
#         with zipfile.ZipFile(zip_filepath, 'r') as zf:
#             zf.extractall(tmpdir)

#         # Cherche les fichiers DICOM récursivement (pour vérification)
#         dcm_files = []
#         for root, dirs, files in os.walk(tmpdir):
#             for f in files:
#                 fpath = os.path.join(root, f)
#                 if f.lower().endswith('.dcm') or _is_dicom(fpath):
#                     dcm_files.append(fpath)

#         if not dcm_files:
#             raise ValueError("Aucun fichier DICOM trouvé dans le ZIP.")

#         print(f"[Preprocess] {len(dcm_files)} fichiers DICOM trouvés.")

#         # ✅ FIX CRITIQUE 3 : cherche la série dans tmpdir (pas seulement le dossier du 1er .dcm)
#         reader     = sitk.ImageSeriesReader()
#         series_ids = reader.GetGDCMSeriesIDs(tmpdir)

#         if not series_ids:
#             raise ValueError("Aucune série DICOM valide trouvée.")

#         series_files = reader.GetGDCMSeriesFileNames(tmpdir, series_ids[0])
#         reader.SetFileNames(series_files)
#         itk_img = reader.Execute()

#         volume  = sitk.GetArrayFromImage(itk_img).astype(np.float32)  # [Z, Y, X] HU
#         spacing = np.array(list(reversed(itk_img.GetSpacing())))       # [Z, Y, X] mm
#         origin  = np.array(list(reversed(itk_img.GetOrigin())))        # [Z, Y, X]

#         # Gestion volume 4D (certains DICOM multi-phase)
#         if volume.ndim == 4:
#             volume  = volume[0]
#             spacing = spacing[1:]
#             print(f"[Preprocess] Volume 4D détecté → squeeze dim 0")

#         print(f"[Preprocess] Volume HU : shape={volume.shape}, spacing={spacing}")
#         return volume, spacing, origin

def read_dicom_zip(zip_filepath: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_filepath, 'r') as zf:
            zf.extractall(tmpdir)

        # ✅ FIX RÉEL : trouver récursivement les dossiers contenant des .dcm
        dicom_dirs = _find_dicom_dirs(tmpdir)

        if not dicom_dirs:
            raise ValueError("Aucun fichier DICOM trouvé dans le ZIP.")

        print(f"[Preprocess] Dossiers DICOM trouvés : {dicom_dirs}")

        reader = sitk.ImageSeriesReader()
        series_files = None

        # Essaie chaque dossier jusqu'à trouver une série valide
        for dicom_dir in dicom_dirs:
            series_ids = reader.GetGDCMSeriesIDs(dicom_dir)
            if series_ids:
                series_files = reader.GetGDCMSeriesFileNames(dicom_dir, series_ids[0])
                print(f"[Preprocess] Série trouvée dans : {dicom_dir}")
                break

        if not series_files:
            raise ValueError("Aucune série DICOM valide trouvée.")

        reader.SetFileNames(series_files)
        itk_img = reader.Execute()

        volume  = sitk.GetArrayFromImage(itk_img).astype(np.float32)
        spacing = np.array(list(reversed(itk_img.GetSpacing())))
        origin  = np.array(list(reversed(itk_img.GetOrigin())))

        if volume.ndim == 4:
            volume  = volume[0]
            spacing = spacing[1:]

        print(f"[Preprocess] Volume HU : shape={volume.shape}, spacing={spacing}")
        return volume, spacing, origin


def _find_dicom_dirs(root: str) -> list:
    """Trouve récursivement tous les dossiers contenant des fichiers DICOM."""
    dicom_dirs = []
    for dirpath, dirs, files in os.walk(root):
        for f in files:
            fpath = os.path.join(dirpath, f)
            if f.lower().endswith('.dcm') or _is_dicom(fpath):
                dicom_dirs.append(dirpath)
                break  # un seul .dcm suffit pour ce dossier
    return dicom_dirs
def _is_dicom(filepath: str) -> bool:
    try:
        with open(filepath, 'rb') as f:
            f.seek(128)
            return f.read(4) == b'DICM'
    except Exception:
        return False


# ─────────────────────────────────────────────────────
# 2. HU → uint8  (✅ FIX IMPORTANT : AVANT resample, comme TiCNet preprocess.py)
# ─────────────────────────────────────────────────────

def HU2uint8(image: np.ndarray, HU_min=-1200.0, HU_max=600.0, HU_nan=-2000.0) -> np.ndarray:
    """
    Convertit les valeurs HU en uint8 [0, 255].
    Identique à HU2uint8() dans preprocess.py TiCNet.

    ✅ FIX IMPORTANT : appelé AVANT resample() pour aligner sur l'ordre TiCNet.
    """
    image_new = np.array(image, dtype=np.float32)
    image_new[np.isnan(image_new)] = HU_nan

    image_new = (image_new - HU_min) / (HU_max - HU_min)
    image_new = np.clip(image_new, 0, 1)
    image_new = (image_new * 255).astype(np.uint8)

    return image_new


# ─────────────────────────────────────────────────────
# 3. RESAMPLE À 1mm  (✅ FIX MINEUR : order=3 pour matcher l'entraînement)
# ─────────────────────────────────────────────────────

def resample(image: np.ndarray, spacing: np.ndarray, new_spacing=None, order=3) -> tuple:
    """
    Resample le volume CT vers new_spacing (défaut 1x1x1 mm).
    Identique à resample() dans preprocess.py TiCNet.

    ✅ FIX MINEUR : order=3 (cubique) par défaut, comme preprocess.py.
    mask_extract.py utilise order=1, mais le volume principal utilise order=3.
    """
    if new_spacing is None:
        new_spacing = np.array([1.0, 1.0, 1.0])

    new_shape       = np.round(np.array(image.shape) * spacing / new_spacing).astype(int)
    resize_factor   = new_shape / np.array(image.shape)
    image_resampled = scipy.ndimage.zoom(image, resize_factor, mode='nearest', order=order)
    actual_spacing  = spacing * np.array(image.shape) / new_shape

    print(f"[Preprocess] Resample : {image.shape} → {image_resampled.shape}")
    return image_resampled, actual_spacing


# ─────────────────────────────────────────────────────
# 4. EXTRACTION MASQUE PULMONAIRE
# ─────────────────────────────────────────────────────

def binarize(image: np.ndarray, spacing: np.ndarray,
             intensity_thred=-600, sigma=1.0,
             area_thred=30.0, eccen_thred=0.99, corner_side=10) -> np.ndarray:
    """
    Binarise le volume CT slice par slice pour isoler les poumons.
    Identique à binarize() dans preprocess.py TiCNet.
    Note: reçoit le volume HU (float32), pas uint8.
    """
    binary_mask = np.zeros(image.shape, dtype=bool)
    side_len    = image.shape[1]
    grid_axis   = np.linspace(-side_len / 2 + 0.5, side_len / 2 - 0.5, side_len)
    x, y        = np.meshgrid(grid_axis, grid_axis)
    distance    = np.sqrt(np.square(x) + np.square(y))
    nan_mask    = (distance < side_len / 2).astype(float)
    nan_mask[nan_mask == 0] = np.nan

    for i in range(image.shape[0]):
        slice_raw = np.array(image[i]).astype('float32')
        num_uniq  = len(np.unique(slice_raw[0:corner_side, 0:corner_side]))
        if num_uniq == 1:
            slice_raw *= nan_mask

        slice_smoothed = scipy.ndimage.gaussian_filter(slice_raw, sigma, truncate=2.0)
        slice_binary   = slice_smoothed < intensity_thred
        label          = measure.label(slice_binary)
        properties     = measure.regionprops(label)
        label_valid    = set()

        for prop in properties:
            area_mm = prop.area * spacing[1] * spacing[2]
            if area_mm > area_thred and prop.eccentricity < eccen_thred:
                label_valid.add(prop.label)

        # ✅ FIX NumPy 2.0 : np.isin au lieu de np.in1d
        slice_binary   = np.isin(label, list(label_valid)).reshape(label.shape)
        binary_mask[i] = slice_binary

    return binary_mask


def volume_filter(label: np.ndarray, spacing: np.ndarray,
                  vol_min=0.2, vol_max=8.2) -> np.ndarray:
    properties = measure.regionprops(label)
    for prop in properties:
        vol = prop.area * spacing.prod()
        if vol < vol_min * 1e6 or vol > vol_max * 1e6:
            label[label == prop.label] = 0
    return label


def exclude_corner_middle(label: np.ndarray) -> np.ndarray:
    mid = int(label.shape[2] / 2)
    corner_label = set([
        label[0, 0, 0],   label[0, 0, -1],
        label[0, -1, 0],  label[0, -1, -1],
        label[-1, 0, 0],  label[-1, 0, -1],
        label[-1, -1, 0], label[-1, -1, -1],
    ])
    middle_label = set([
        label[0, 0, mid],  label[0, -1, mid],
        label[-1, 0, mid], label[-1, -1, mid],
    ])
    for l in corner_label:
        label[label == l] = 0
    for l in middle_label:
        label[label == l] = 0
    return label


def fill_hole(binary_mask: np.ndarray) -> np.ndarray:
    label = measure.label(~binary_mask)
    corner_label = set([
        label[0, 0, 0],   label[0, 0, -1],
        label[0, -1, 0],  label[0, -1, -1],
        label[-1, 0, 0],  label[-1, 0, -1],
        label[-1, -1, 0], label[-1, -1, -1],
    ])
    # ✅ FIX NumPy 2.0 : np.isin au lieu de np.in1d
    binary_mask = ~np.isin(label, list(corner_label)).reshape(label.shape)
    return binary_mask


def exclude_air(label: np.ndarray, spacing: np.ndarray,
                area_thred=3e3, dist_thred=62) -> tuple:
    y_axis   = np.linspace(-label.shape[1]/2+0.5, label.shape[1]/2-0.5, label.shape[1]) * spacing[1]
    x_axis   = np.linspace(-label.shape[2]/2+0.5, label.shape[2]/2-0.5, label.shape[2]) * spacing[2]
    y, x     = np.meshgrid(y_axis, x_axis)
    distance = np.sqrt(np.square(y) + np.square(x))
    dist_max = np.max(distance)

    vols        = measure.regionprops(label)
    label_valid = set()

    for vol in vols:
        single_vol   = (label == vol.label)
        slice_area   = np.zeros(label.shape[0])
        min_distance = np.zeros(label.shape[0])

        for i in range(label.shape[0]):
            slice_area[i]   = np.sum(single_vol[i]) * np.prod(spacing[1:3])
            min_distance[i] = np.min(single_vol[i] * distance +
                                     (1 - single_vol[i]) * dist_max)

        valid_slices = [min_distance[i] for i in range(label.shape[0])
                        if slice_area[i] > area_thred]
        if valid_slices and np.average(valid_slices) < dist_thred:
            label_valid.add(vol.label)

    # ✅ FIX NumPy 2.0 : np.isin au lieu de np.in1d
    binary_mask = np.isin(label, list(label_valid)).reshape(label.shape)
    has_lung    = len(label_valid) > 0
    return binary_mask, has_lung


def convex_hull_dilate(binary_mask: np.ndarray,
                       dilate_factor=1.5, iterations=10) -> np.ndarray:
    binary_mask_dilated = np.array(binary_mask)
    for i in range(binary_mask.shape[0]):
        slice_binary = binary_mask[i]
        if np.sum(slice_binary) > 0:
            slice_convex = morphology.convex_hull_image(slice_binary)
            if np.sum(slice_convex) <= dilate_factor * np.sum(slice_binary):
                binary_mask_dilated[i] = slice_convex

    struct = scipy.ndimage.generate_binary_structure(3, 1)
    binary_mask_dilated = scipy.ndimage.binary_dilation(
        binary_mask_dilated, structure=struct, iterations=iterations)
    return binary_mask_dilated


def extract_lung(image: np.ndarray, spacing: np.ndarray) -> np.ndarray:
    """
    Extrait le masque pulmonaire complet.
    Identique à extract_lung() dans preprocess.py TiCNet.
    Reçoit le volume HU brut (avant uint8) pour que le seuil -600 HU soit valide.
    """
    print("[Preprocess] Extraction masque pulmonaire...")
    binary_mask           = binarize(image, spacing)
    label                 = measure.label(binary_mask, connectivity=1)
    label                 = exclude_corner_middle(label)
    label                 = volume_filter(label, spacing)
    binary_mask, has_lung = exclude_air(label, spacing)
    binary_mask           = fill_hole(binary_mask)
    print(f"[Preprocess] Masque pulmonaire : has_lung={has_lung}")
    return binary_mask


# ─────────────────────────────────────────────────────
# 5. APPLY MASK
#    ✅ FIX IMPORTANT : split gauche/droite par composantes connexes
#    (pas par coupure au milieu X qui peut masquer des poumons asymétriques)
# ─────────────────────────────────────────────────────

def apply_mask(image: np.ndarray, binary_mask: np.ndarray, pad_value=170) -> np.ndarray:
    """
    Applique le masque pulmonaire — zones hors poumon → pad_value.

    ✅ FIX IMPORTANT : identifie les 2 poumons via les 2 plus grandes
    composantes connexes (robuste à l'asymétrie anatomique et aux patients
    en position non-standard), au lieu de couper au milieu X.
    """
    # Trouve les 2 plus grandes composantes connexes = poumon gauche + droit
    label = measure.label(binary_mask)
    props = measure.regionprops(label)

    if len(props) == 0:
        # Aucune composante → pas de masque, retourne uint8 direct
        return (image * binary_mask + pad_value * (~binary_mask).astype(np.uint8)).astype(np.uint8)

    # Trie par volume décroissant, garde les 2 plus grandes
    props_sorted = sorted(props, key=lambda p: p.area, reverse=True)[:2]

    binary_mask1 = (label == props_sorted[0].label)
    if len(props_sorted) > 1:
        binary_mask2 = (label == props_sorted[1].label)
    else:
        binary_mask2 = np.zeros_like(binary_mask1)

    binary_mask1_dilated = convex_hull_dilate(binary_mask1)
    binary_mask2_dilated = convex_hull_dilate(binary_mask2)
    binary_mask_dilated  = binary_mask1_dilated | binary_mask2_dilated

    image_new = (image * binary_mask_dilated +
                 pad_value * (~binary_mask_dilated).astype(np.uint8))
    return image_new.astype(np.uint8)


# ─────────────────────────────────────────────────────
# 6. CROP AUTOUR DU POUMON
# ─────────────────────────────────────────────────────

def get_lung_box(binary_mask: np.ndarray, new_shape: np.ndarray, margin=5) -> np.ndarray:
    # Force 3D
    if binary_mask.ndim == 4:
        binary_mask = binary_mask[0]

    z_true, y_true, x_true = np.where(binary_mask)

    # Aucun poumon trouvé → retourne volume entier
    if len(z_true) == 0:
        return np.array([
            [0, new_shape[0]],
            [0, new_shape[1]],
            [0, new_shape[2]],
        ])

    old_shape = np.array(binary_mask.shape[:3], dtype=np.float64)
    new_shape = np.array(new_shape[:3],         dtype=np.float64)

    lung_box = np.array([
        [np.min(z_true), np.max(z_true)],
        [np.min(y_true), np.max(y_true)],
        [np.min(x_true), np.max(x_true)],
    ], dtype=np.float64)

    lung_box = lung_box * np.expand_dims(new_shape, 1) / np.expand_dims(old_shape, 1)
    lung_box = np.floor(lung_box).astype(int)

    lung_box[0] = (max(0, lung_box[0, 0] - margin),
                   min(int(new_shape[0]), lung_box[0, 1] + margin))
    lung_box[1] = (max(0, lung_box[1, 0] - margin),
                   min(int(new_shape[1]), lung_box[1, 1] + margin))
    lung_box[2] = (max(0, lung_box[2, 0] - margin),
                   min(int(new_shape[2]), lung_box[2, 1] + margin))

    return lung_box


# ─────────────────────────────────────────────────────
# 7. PIPELINE COMPLET
# ─────────────────────────────────────────────────────

def preprocess_dicom_zip(zip_filepath: str, save_dir: str = None, pid: str = None) -> np.ndarray:
    """
    Pipeline complet DICOM ZIP → volume préprocessé prêt pour TiCNet.

    ✅ FIX CRITIQUE 1 : retourne uint8, PAS float32
    ✅ FIX CRITIQUE 2 : sauvegarde les 4 fichiers sur disque si save_dir fourni :
        {pid}_seg.nrrd      ← volume préprocessé (lu par BboxReader)
        {pid}_origin.npy    ← origine spatiale (pour conversion coords monde→voxel)
        {pid}_spacing.npy   ← spacing après resample
        {pid}_ebox.npy      ← extended bounding box du crop
    ✅ FIX IMPORTANT : HU2uint8 AVANT resample (ordre aligné sur TiCNet)
    ✅ FIX IMPORTANT : split poumons par composantes connexes (pas coupe X)
    ✅ FIX MINEUR : resample order=3

    Retourne un array uint8 [Z, Y, X] avec pad_value=170.
    """
    # 1. Lit le DICOM
    volume_hu, spacing, origin = read_dicom_zip(zip_filepath)

    # ✅ ORDRE CORRIGÉ — identique à TiCNet preprocess.py :
    # 2. HU → uint8 EN PREMIER (avant resample)
    volume_uint8 = HU2uint8(volume_hu)
    print(f"[Preprocess] uint8 avant resample : min={volume_uint8.min()}, max={volume_uint8.max()}")

    # 3. Resample à 1mm (order=3 pour matcher l'entraînement)
    volume_resampled, new_spacing = resample(volume_uint8.astype(np.float32), spacing, order=3)
    volume_resampled = np.clip(volume_resampled, 0, 255).astype(np.uint8)
    print(f"[Preprocess] Après resample uint8 : min={volume_resampled.min()}, max={volume_resampled.max()}")

    # 4. Extraction masque pulmonaire sur HU brut (le seuil -600 HU doit être en HU)
    try:
        # Resample le volume HU aussi (pour avoir le bon spacing pour binarize)
        volume_hu_resampled, _ = resample(volume_hu, spacing, order=1)
        binary_mask = extract_lung(volume_hu_resampled, new_spacing)
    except Exception as e:
        print(f"[Preprocess] Avertissement extraction masque : {e}")
        print("[Preprocess] Utilisation du volume sans masque.")
        binary_mask = None

    if binary_mask is not None:
        # 5. Apply mask (split par composantes connexes)
        try:
            volume_masked = apply_mask(volume_resampled, binary_mask, pad_value=170)
        except Exception as e:
            print(f"[Preprocess] Avertissement apply_mask : {e}")
            volume_masked = volume_resampled

        # 6. Crop autour du poumon
        try:
            lung_box = get_lung_box(
                binary_mask,
                np.array(volume_masked.shape[:3])
            )
            z_min, z_max = lung_box[0]
            y_min, y_max = lung_box[1]
            x_min, x_max = lung_box[2]
            volume_cropped = volume_masked[z_min:z_max, y_min:y_max, x_min:x_max]
            print(f"[Preprocess] Crop poumon : {volume_masked.shape} → {volume_cropped.shape}")
            ebox = np.array([z_min, y_min, x_min])
        except Exception as e:
            print(f"[Preprocess] Avertissement crop : {e}")
            volume_cropped = volume_masked
            ebox = np.array([0, 0, 0])
    else:
        volume_cropped = volume_resampled
        ebox = np.array([0, 0, 0])

    # ✅ FIX CRITIQUE 1 : retourne uint8 (pas float32)
    # BboxReader lit le _seg.nrrd en uint8 et applique (x-128)/128 lui-même
    volume_final = volume_cropped.astype(np.uint8)

    # ✅ FIX CRITIQUE 2 : sauvegarde les 4 fichiers sur disque
    if save_dir is not None and pid is not None:
        os.makedirs(save_dir, exist_ok=True)

        # Fichier principal — lu par BboxReader en mode eval
        nrrd.write(os.path.join(save_dir, f'{pid}_seg.nrrd'), volume_final)

        # Métadonnées spatiales — pour conversion coordonnées monde→voxel
        np.save(os.path.join(save_dir, f'{pid}_origin.npy'),  origin)
        np.save(os.path.join(save_dir, f'{pid}_spacing.npy'), new_spacing)
        np.save(os.path.join(save_dir, f'{pid}_ebox.npy'),    ebox)

        print(f"[Preprocess] Fichiers sauvegardés dans {save_dir}/")
        print(f"  → {pid}_seg.nrrd   shape={volume_final.shape}")
        print(f"  → {pid}_origin.npy  {origin}")
        print(f"  → {pid}_spacing.npy {new_spacing}")
        print(f"  → {pid}_ebox.npy    {ebox}")

    return volume_final