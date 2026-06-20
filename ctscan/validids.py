# import pandas as pd

# # 1. Charger la liste des seriesuid du fold (ex: 2_val.csv) - pas de header
# val_pids = pd.read_csv('//home//inas//lung_cancer_backend//ticnet//split//2_val.csv', header=None, names=['seriesuid'])['seriesuid'].tolist()

# # 2. Charger le fichier d'annotations
# annos = pd.read_csv('//home//inas//lung_cancer_backend//ticnet//annotations//annotations.csv')  # colonnes: seriesuid,coordX,coordY,coordZ,diameter_mm

# # 3. Filtrer les annotations dont le seriesuid est dans val_pids
# filtered = annos[annos['seriesuid'].isin(val_pids)]

# # 4. Stats : combien de pids du val ont au moins une annotation
# pids_with_annos = filtered['seriesuid'].unique()
# print(f"Nombre de pids dans val.csv : {len(val_pids)}")
# print(f"Nombre de pids ayant au moins une annotation : {len(pids_with_annos)}")
# print(f"Nombre total d'annotations correspondantes : {len(filtered)}")

# # Optionnel: pids sans aucune annotation (scans sans nodule)
# pids_without_annos = set(val_pids) - set(pids_with_annos)
# print(f"Nombre de pids sans annotation : {len(pids_without_annos)}")

# # 5. Sauvegarder le résultat
# filtered.to_csv('val_filtered_annotations.csv', index=False)
# print("Fichier sauvegardé : val_filtered_annotations.csv")








import pandas as pd

# 1. Charger la liste des seriesuid du fold (ex: 2_val.csv) - pas de header
val_pids = pd.read_csv('//home//inas//lung_cancer_backend//ticnet//split//2_val.csv', header=None, names=['seriesuid'])['seriesuid'].tolist()

# 2. Charger le fichier d'annotations
annos = pd.read_csv('//home//inas//lung_cancer_backend//ticnet//annotations//annotations.csv')  # colonnes: seriesuid,coordX,coordY,coordZ,diameter_mm

# 3. Filtrer les annotations dont le seriesuid est dans val_pids
filtered = annos[annos['seriesuid'].isin(val_pids)]

# 4. Stats : combien de pids du val ont au moins une annotation
pids_with_annos = filtered['seriesuid'].unique()
print(f"Nombre de pids dans val.csv : {len(val_pids)}")
print(f"Nombre de pids ayant au moins une annotation : {len(pids_with_annos)}")
print(f"Nombre total d'annotations correspondantes : {len(filtered)}")

# Optionnel: pids sans aucune annotation (scans sans nodule)
pids_without_annos = set(val_pids) - set(pids_with_annos)
print(f"Nombre de pids sans annotation : {len(pids_without_annos)}")

# 5. Sauvegarder le résultat (toutes les annotations des pids du val)
filtered.to_csv('//home//inas//lung_cancer_backend//ticnet//split//val_filtered_annotations.csv', index=False)
print("Fichier sauvegardé : val_filtered_annotations.csv")

# 6. Exporter la liste des pids ayant au moins un nodule (1 colonne, sans header)
pd.Series(pids_with_annos, name='seriesuid').to_csv('//home//inas//lung_cancer_backend//ticnet//split//val_pids_with_nodule.csv', index=False, header=False)
print("Fichier sauvegardé : val_pids_with_nodule.csv")