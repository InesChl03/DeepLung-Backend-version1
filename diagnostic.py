import torch
import sys
import os

os.chdir(r'C:\Users\PC\Desktop\lung_cancer_backend\lung_cancer_backend')
sys.path.insert(0, '.')
sys.path.insert(0, 'TiCNet')

pth_path = 'analyse/models/120.pth'

checkpoint = torch.load(pth_path, map_location='cpu')

print("=" * 60)
print("CHECKPOINT KEYS:", list(checkpoint.keys()))
state_dict = checkpoint['state_dict']

print("\nCouches du .pth:")
for k in list(state_dict.keys())[:15]:
    print("  " + k + " : " + str(state_dict[k].shape))

from net.main_net import build_model
from config import net_config

model = build_model(net_config)
model_keys = list(model.state_dict().keys())

print("\nCouches du modele actuel:")
for k in model_keys[:15]:
    print("  " + k)

pth_keys_set   = set(state_dict.keys())
model_keys_set = set(model.state_dict().keys())

missing    = model_keys_set - pth_keys_set
unexpected = pth_keys_set - model_keys_set

print("\n" + "=" * 60)
print("Cles manquantes  : " + str(len(missing)))
print("Cles inattendues : " + str(len(unexpected)))

if missing:
    print("\nExemples manquants:")
    for k in list(missing)[:10]:
        print("  " + k)

if unexpected:
    print("\nExemples inattendus:")
    for k in list(unexpected)[:10]:
        print("  " + k)

if not missing and not unexpected:
    print("\nArchitecture compatible - probleme vient du seuil RPN")
else:
    print("\nMismatch architecture detecte")