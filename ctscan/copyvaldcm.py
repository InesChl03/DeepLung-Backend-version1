import os
import csv
import shutil

# Fichier contenant seriesuid,path (généré précédemment)
input_csv = "val_pids_with_nodule_paths.csv"

# Dossier de destination
dest_root = "/mnt/d/maroua/val_pids_with_nodule"
os.makedirs(dest_root, exist_ok=True)

copied = 0
skipped = 0

with open(input_csv, "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pid = row["seriesuid"]
        src = row["path"]

        if not src:
            print(f"[SKIP] pas de chemin pour {pid}")
            skipped += 1
            continue

        dst = os.path.join(dest_root, pid)

        if os.path.exists(dst):
            print(f"[EXISTE DEJA] {pid}")
            continue

        print(f"Copie de {src} -> {dst}")
        try:
          shutil.copytree(src, dst, copy_function=shutil.copyfile)
        except shutil.Error:
           pass  # erreurs de copystat sur dossier drvfs, contenu déjà copié
        copied += 1

print(f"\nTermine. {copied} dossiers copies, {skipped} ignores.")
print(f"Destination : {dest_root}")