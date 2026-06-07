import numpy as np
import SimpleITK as sitk

mhd_path = "/mnt/c/Users/PC/Downloads/lunatest/lunatest/1.3.6.1.4.1.14519.5.2.1.6279.6001.100225287222365663678666836860.mhd"

itkimage = sitk.ReadImage(mhd_path)
origin  = np.array(list(reversed(itkimage.GetOrigin())))
spacing = np.array(list(reversed(itkimage.GetSpacing())))
shape   = np.array(list(reversed(itkimage.GetSize())))

print(f"Origin  (z,y,x) : {origin}")
print(f"Spacing (z,y,x) : {spacing}")
print(f"Shape   (z,y,x) : {shape}")

# Annotations LUNA16 (X, Y, Z monde)
annotations = [
    {"x": -128.6994211, "y": -175.3192718, "z": -298.3875064, "diameter_mm": 5.651470635},
    {"x": 103.7836509,  "y": -211.9251487, "z": -227.12125,   "diameter_mm": 4.224708481},
]

# Tes détections après preprocessing (voxel dans espace preprocessé)
detections = [
    {"z": 125.80, "y": 100.90, "x": 23.64,  "diameter_mm": 13.51, "probability": 0.9887},
    {"z": 197.77, "y": 64.62,  "x": 255.90, "diameter_mm": 12.47, "probability": 0.8768},
    {"z": 301.94, "y": 165.88, "x": 233.11, "diameter_mm": 12.32, "probability": 0.5313},
    {"z": 106.27, "y": 122.00, "x": 20.77,  "diameter_mm": 12.25, "probability": 0.5717},
    {"z": 224.60, "y": 182.08, "x": 273.98, "diameter_mm": 15.25, "probability": 0.5504},
    {"z": 84.06,  "y": 125.52, "x": 185.83, "diameter_mm": 12.85, "probability": 0.5394},
    {"z": 57.84,  "y": 189.97, "x": 265.92, "diameter_mm": 12.01, "probability": 0.5088},
    {"z": 213.38, "y": 186.29, "x": 224.72, "diameter_mm": 11.84, "probability": 0.5270},
    {"z": 193.28, "y": 113.42, "x": 292.41, "diameter_mm": 13.32, "probability": 0.5035},
    {"z": 169.25, "y": 114.27, "x": 105.63, "diameter_mm": 19.31, "probability": 0.5282},
]

# Paramètres du preprocessing appliqué
# Shape après resample : (349, 330, 330)
# Shape après crop     : (280, 264, 264) → ebox estimé
original_shape   = np.array([194, 512, 512])
resampled_shape  = np.array([349, 330, 330])
new_spacing      = spacing * original_shape / resampled_shape

# ebox : début du crop (z_min, y_min, x_min) dans l'espace resampleé
# Shape après crop = 280, 264, 264
# crop = 10% à 90% de chaque dimension
ebox = np.array([
    int(resampled_shape[0] * 0.1),
    int(resampled_shape[1] * 0.1),
    int(resampled_shape[2] * 0.1)
])
print(f"\nNew spacing : {new_spacing}")
print(f"Ebox (crop start) : {ebox}")

print("\n--- Annotations converties dans espace preprocessé ---")
for i, ann in enumerate(annotations):
    # monde → voxel original
    vox_z = (ann['z'] - origin[0]) / spacing[0]
    vox_y = (ann['y'] - origin[1]) / spacing[1]
    vox_x = (ann['x'] - origin[2]) / spacing[2]

    # voxel original → voxel resampleé
    vox_z_r = vox_z * spacing[0] / new_spacing[0]
    vox_y_r = vox_y * spacing[1] / new_spacing[1]
    vox_x_r = vox_x * spacing[2] / new_spacing[2]

    # voxel resampleé → voxel après crop
    vox_z_c = vox_z_r - ebox[0]
    vox_y_c = vox_y_r - ebox[1]
    vox_x_c = vox_x_r - ebox[2]

    print(f"  Nodule {i+1}: voxel preprocessé=({vox_z_c:.1f}, {vox_y_c:.1f}, {vox_x_c:.1f}), diameter={ann['diameter_mm']:.2f}mm")

print("\n--- Comparaison ---")
for i, ann in enumerate(annotations):
    vox_z = (ann['z'] - origin[0]) / spacing[0]
    vox_y = (ann['y'] - origin[1]) / spacing[1]
    vox_x = (ann['x'] - origin[2]) / spacing[2]

    vox_z_r = vox_z * spacing[0] / new_spacing[0]
    vox_y_r = vox_y * spacing[1] / new_spacing[1]
    vox_x_r = vox_x * spacing[2] / new_spacing[2]

    vox_z_c = vox_z_r - ebox[0]
    vox_y_c = vox_y_r - ebox[1]
    vox_x_c = vox_x_r - ebox[2]

    best_dist = float('inf')
    best_det  = None

    for det in detections:
        dist = np.sqrt(
            (det['z'] - vox_z_c)**2 +
            (det['y'] - vox_y_c)**2 +
            (det['x'] - vox_x_c)**2
        )
        if dist < best_dist:
            best_dist = dist
            best_det  = det

    # Distance en mm
    dist_mm = best_dist * new_spacing[0]
    radius_mm = ann['diameter_mm'] / 2.0
    detected = dist_mm <= radius_mm
    status = "✅ DÉTECTÉ" if detected else "❌ MANQUÉ"

    print(f"\n  Annotation {i+1} : preprocessed=({vox_z_c:.1f}, {vox_y_c:.1f}, {vox_x_c:.1f})")
    print(f"  Meilleure détection : z={best_det['z']:.1f}, y={best_det['y']:.1f}, x={best_det['x']:.1f}")
    print(f"  Distance : {dist_mm:.1f} mm | Rayon annoté : {radius_mm:.1f} mm")
    print(f"  Probabilité : {best_det['probability']:.4f}")
    print(f"  Résultat : {status}")