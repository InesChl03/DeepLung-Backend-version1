import os
import csv

# Dossier racine LIDC-IDRI
lidc_root = "/mnt/d/maroua/lidc_idri"

# Fichier contenant les seriesuid (pids) du val ayant au moins un nodule
pids_file = "//home//inas//lung_cancer_backend//ticnet//split//val_pids_with_nodule.csv"

# Charger la liste des pids recherchés
with open(pids_file, "r") as f:
    pids = set(line.strip() for line in f if line.strip())

print(f"Nombre de pids recherchés : {len(pids)}")

found = {}  # pid -> chemin complet

# Parcourir récursivement l'arborescence LIDC-IDRI
for dirpath, dirnames, filenames in os.walk(lidc_root):
    folder_name = os.path.basename(dirpath)
    if folder_name in pids:
        found[folder_name] = dirpath

print(f"Nombre de pids trouvés : {len(found)}")

# pids non trouvés (pour vérification)
not_found = pids - set(found.keys())
if not_found:
    print(f"Pids NON trouvés ({len(not_found)}) :")
    for pid in not_found:
        print(" -", pid)

# Exporter le résultat dans un CSV: seriesuid, chemin
output_file = "val_pids_with_nodule_paths.csv"
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["seriesuid", "path"])
    for pid in pids:
        writer.writerow([pid, found.get(pid, "")])

print(f"Fichier sauvegardé : {output_file}")