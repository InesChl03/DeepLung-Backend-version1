"""
dicom_to_mhd.py — DICOM folder → .mhd + .raw conversion
=========================================================
Converts a clinical DICOM CT series into the exact .mhd/.raw format
used by LUNA16, so the existing TiCNet inference pipeline works unchanged.

Usage (standalone):
    mhd_path, raw_path = convert_dicom_to_mhd(dicom_folder, output_dir)
    result = analyser_ctscan(mhd_path, raw_path)

Integration in Django views.py:
    from .dicom_to_mhd import convert_dicom_to_mhd
"""

import os
import logging
import tempfile

import SimpleITK as sitk

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Core conversion
# ─────────────────────────────────────────────────────────────────────────────

def convert_dicom_to_mhd(dicom_folder: str,
                          output_dir: str = None,
                          output_name: str = "scan") -> tuple[str, str]:
    """
    Convert a DICOM CT series folder into a .mhd + .raw pair.

    The output is pixel/metadata-equivalent to LUNA16 .mhd files:
      - Original HU values preserved (int16)
      - Original voxel spacing preserved (mm)
      - Origin and direction cosines preserved in .mhd header
      - Slices sorted in correct anatomical order automatically

    Args:
        dicom_folder (str): Path to folder containing .dcm files of ONE series.
        output_dir   (str): Where to write scan.mhd + scan.raw.
                            If None, a temp directory is created automatically.
        output_name  (str): Base filename without extension (default: "scan").

    Returns:
        (mhd_path, raw_path): absolute paths ready to pass to analyser_ctscan()

    Raises:
        ValueError: if no DICOM series is found in the folder.
        RuntimeError: if reading or writing fails.
    """

    # ── 1. Validate input ────────────────────────────────────────────────────
    if not os.path.isdir(dicom_folder):
        raise ValueError(f"[DICOM→MHD] Folder not found: {dicom_folder}")

    dcm_files = [f for f in os.listdir(dicom_folder)
                 if f.lower().endswith('.dcm')]
    if not dcm_files:
        raise ValueError(
            f"[DICOM→MHD] No .dcm files found in: {dicom_folder}"
        )

    logger.info(f"[DICOM→MHD] Found {len(dcm_files)} DICOM files in {dicom_folder}")

    # ── 2. Detect available series ───────────────────────────────────────────
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(dicom_folder)

    if not series_ids:
        raise ValueError(
            f"[DICOM→MHD] SimpleITK found no valid DICOM series in: {dicom_folder}"
        )

    # If multiple series exist, pick the one with the most slices (CT volume)
    if len(series_ids) > 1:
        logger.warning(
            f"[DICOM→MHD] {len(series_ids)} series found — selecting largest"
        )
        best_series = max(
            series_ids,
            key=lambda sid: len(reader.GetGDCMSeriesFileNames(dicom_folder, sid))
        )
    else:
        best_series = series_ids[0]

    logger.info(f"[DICOM→MHD] Using series UID: {best_series}")

    # ── 3. Load the series ───────────────────────────────────────────────────
    dicom_files = reader.GetGDCMSeriesFileNames(dicom_folder, best_series)
    logger.info(f"[DICOM→MHD] Loading {len(dicom_files)} slices...")

    reader.SetFileNames(dicom_files)

    # Critical metadata flags:
    #   MetaDataDictionaryArrayUpdateOn  → reads per-slice tags
    #   LoadPrivateTagsOn                → preserves private DICOM tags
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()

    try:
        image = reader.Execute()
    except Exception as e:
        raise RuntimeError(f"[DICOM→MHD] Failed to read DICOM series: {e}")

    # ── 4. Validate the loaded volume ────────────────────────────────────────
    size    = image.GetSize()        # (W, H, D) in SimpleITK convention
    spacing = image.GetSpacing()     # (sx, sy, sz) in mm
    origin  = image.GetOrigin()      # (ox, oy, oz) in mm

    logger.info(f"[DICOM→MHD] Volume size    : W={size[0]}, H={size[1]}, D={size[2]}")
    logger.info(f"[DICOM→MHD] Voxel spacing  : {spacing[0]:.4f} x {spacing[1]:.4f} x {spacing[2]:.4f} mm")
    logger.info(f"[DICOM→MHD] Origin         : {origin}")

    if size[2] < 10:
        logger.warning(
            f"[DICOM→MHD] Only {size[2]} slices — this may not be a full CT volume"
        )

    # ── 5. Cast to int16 — identical to LUNA16 native format ────────────────
    #
    # LUNA16 .mhd files store raw HU values as int16 (MET_SHORT).
    # Clinical DICOM pixel data is also int16 after rescale intercept/slope.
    # SimpleITK applies RescaleIntercept/RescaleSlope automatically on read,
    # so the image already contains true HU values — we just cast to int16.
    #
    image = sitk.Cast(image, sitk.sitkInt16)
    logger.info("[DICOM→MHD] Cast to int16 (MET_SHORT) — matches LUNA16 format")

    # ── 6. Prepare output paths ──────────────────────────────────────────────
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix='dicom2mhd_')
        logger.info(f"[DICOM→MHD] Auto temp dir: {output_dir}")
    else:
        os.makedirs(output_dir, exist_ok=True)

    mhd_path = os.path.join(output_dir, f"{output_name}.mhd")
    raw_path  = os.path.join(output_dir, f"{output_name}.raw")

    # ── 7. Write .mhd + .raw ─────────────────────────────────────────────────
    #
    # SimpleITK automatically writes the companion .raw file when the
    # output extension is .mhd. Spacing, origin, and direction are
    # written into the .mhd header — identical to LUNA16 files.
    #
    try:
        sitk.WriteImage(image, mhd_path, useCompression=False)
    except Exception as e:
        raise RuntimeError(f"[DICOM→MHD] Failed to write .mhd/.raw: {e}")

    # Verify both files were created
    if not os.path.isfile(mhd_path):
        raise RuntimeError(f"[DICOM→MHD] .mhd file was not created: {mhd_path}")
    if not os.path.isfile(raw_path):
        raise RuntimeError(f"[DICOM→MHD] .raw file was not created: {raw_path}")

    mhd_size_kb = os.path.getsize(mhd_path) / 1024
    raw_size_mb = os.path.getsize(raw_path) / (1024 * 1024)
    logger.info(f"[DICOM→MHD] Written: {mhd_path} ({mhd_size_kb:.1f} KB)")
    logger.info(f"[DICOM→MHD] Written: {raw_path} ({raw_size_mb:.1f} MB)")
    logger.info("[DICOM→MHD] Conversion successful ✓")

    return mhd_path, raw_path


# ─────────────────────────────────────────────────────────────────────────────
# Django integration helper
# ─────────────────────────────────────────────────────────────────────────────

def analyser_depuis_dicom(dicom_folder: str) -> dict:
    """
    Full pipeline: DICOM folder → .mhd/.raw → TiCNet inference.

    This is the single function to call from Django views.py when
    the uploaded input is a DICOM folder instead of .mhd/.raw files.

    Args:
        dicom_folder (str): path to folder containing .dcm files

    Returns:
        dict: same structure as analyser_ctscan() returns:
              {
                "nodules": list[dict],
                "origin":  [z, y, x],
                "spacing": [z, y, x],
                "ebox":    [z, y, x],
                "duree":   float
              }
    """
    import shutil
    import tempfile

    # Use a single temp dir for both conversion output and inference
    tmp_dir = tempfile.mkdtemp(prefix='dicom_pipeline_')

    try:
        # Step 1: DICOM → .mhd + .raw
        mhd_path, raw_path = convert_dicom_to_mhd(
            dicom_folder=dicom_folder,
            output_dir=tmp_dir,
            output_name="scan"
        )

        # Step 2: existing TiCNet pipeline — completely unchanged
        from .inference import analyser_ctscan
        result = analyser_ctscan(mhd_path, raw_path)

        return result

    finally:
        # Clean up temp directory after inference completes
        shutil.rmtree(tmp_dir, ignore_errors=True)