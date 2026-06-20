"""
net/transformer.py
==================
Remplace le Transformer DETR original de TiCNet
par le Swin Transformer 3D de MONAI.

Corrections appliquées vs version précédente :
  1. Suppression de src + pos_embed — Swin utilise déjà un relative
     position bias interne. Ajouter pos_embed manuellement perturbe
     l'apprentissage sans apporter d'information supplémentaire.
  2. swin_embed_dim=48 au lieu de 24 — donne plus de capacité au Swin
     pour représenter les features sur les petits volumes (4×4×4).

Interface identique à l'original :
    build_transformer(cfg)  ->  instance Transformer
    Transformer.forward(src, pos_embed)  ->  Tensor (B, C, D, H, W)

Aucun changement dans feature_net.py ou main_net.py.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from monai.networks.nets.swin_unetr import SwinTransformer


class Transformer(nn.Module):
    """
    Swin Transformer 3D MONAI — remplace le Transformer DETR original.

    Entrée  : src (B, C, D, H, W)  +  pos_embed (B, C, D, H, W)
    Sortie  : (B, C, D, H, W)  — forme strictement identique à l'entrée

    Différences clés vs Transformer DETR original :
      - DETR : attention globale O(N²) sur tous les tokens + pos_embed manuel
      - Swin  : shifted window attention locale + relative position bias interne
               → pas besoin de pos_embed externe (ignoré proprement)
               → fonctionne sur toutes les tailles (train fixe + test variable)
    """

    def __init__(
        self,
        d_model: int = 64,
        nhead: int = 8,
        num_queries: int = 512,
        num_encoder_layers: int = 6,
        num_decoder_layers: int = 6,
        dim_feedforward: int = 256,
        dropout: float = 0.1,
        activation: str = "relu",
        normalize_before: bool = False,
        return_intermediate_dec: bool = False,
        window_size: int = 2,
        swin_embed_dim: int = 48,      # 48 >> 24 : meilleure capacité
    ):
        super().__init__()
        self.d_model = d_model
        self.nhead = nhead

        # ── Swin Transformer 3D MONAI ─────────────────────────────────────────
        # window_size=2 : adapté à out4=(4,4,4) après 4 maxpools
        # patch_size=(2,2,2) : réduit 4×4×4 → 2×2×2 au 1er stage
        # depths=(2,2,2,2) : 4 stages, 2 blocs chacun
        # num_heads=(4,8,8,8) : progressif, standard pour embed_dim=48
        self.swin = SwinTransformer(
            in_chans=d_model,
            embed_dim=swin_embed_dim,
            window_size=(window_size, window_size, window_size),
            patch_size=(2, 2, 2),
            depths=(2, 2, 2, 2),
            num_heads=(4, 8, 8, 8),    # progressif, adapté à embed_dim=48
            mlp_ratio=4.0,
            qkv_bias=True,
            drop_rate=dropout,
            attn_drop_rate=dropout,
            drop_path_rate=0.1,
            spatial_dims=3,
            use_checkpoint=False,
        )

        # ── Projection de sortie ──────────────────────────────────────────────
        # hidden[0] : (B, swin_embed_dim, ceil(D/2), ceil(H/2), ceil(W/2))
        # F.interpolate restaure (D, H, W) exact, y compris dimensions impaires
        # Conv1×1 restaure d_model channels
        self.output_conv = nn.Sequential(
            nn.Conv3d(swin_embed_dim, d_model, kernel_size=1),
            nn.BatchNorm3d(d_model),
            nn.ReLU(inplace=True),
        )

    def forward(self, src, pos_embed):
        """
        src       : (B, C, D, H, W)
        pos_embed : (B, C, D, H, W)  — accepté pour compatibilité interface
                    mais NON utilisé : Swin a son propre relative position bias
        return    : (B, C, D, H, W)
        """
        B, C, D, H, W = src.shape

        # ── Swin Transformer 3D ───────────────────────────────────────────────
        # On passe src DIRECTEMENT, sans ajouter pos_embed.
        # Raison : SwinTransformer calcule un relative position bias interne
        # dans chaque WindowAttention. Ajouter pos_embed externe en plus
        # double l'information de position et perturbe l'apprentissage.
        hidden = self.swin(src)
        # hidden[0] shape : (B, swin_embed_dim, ceil(D/2), ceil(H/2), ceil(W/2))

        # ── Restaurer la résolution d'entrée (D, H, W) ───────────────────────
        # trilinear + align_corners=False : stable même sur dimensions impaires
        x = F.interpolate(
            hidden[0],
            size=(D, H, W),
            mode='trilinear',
            align_corners=False
        )

        # ── Restaurer le nombre de channels ──────────────────────────────────
        x = self.output_conv(x)

        # ── Connexion résiduelle ──────────────────────────────────────────────
        return x + src


def build_transformer(cfg):
    """
    Interface identique à l'originale.
    Appelé dans feature_net.py : self.transformer = build_transformer(config)

    Paramètres lus depuis net_config :
        hidden_dim, dropout, nheads, num_queries,
        dim_feedforward, enc_layers, dec_layers, pre_norm,
        swin_window_size  (défaut: 2)
        swin_embed_dim    (défaut: 48)
    """
    return Transformer(
        d_model=cfg['hidden_dim'],
        dropout=cfg['dropout'],
        nhead=cfg['nheads'],
        num_queries=cfg['num_queries'],
        dim_feedforward=cfg['dim_feedforward'],
        num_encoder_layers=cfg['enc_layers'],
        num_decoder_layers=cfg['dec_layers'],
        normalize_before=cfg['pre_norm'],
        return_intermediate_dec=True,
        window_size=cfg.get('swin_window_size', 2),
        swin_embed_dim=cfg.get('swin_embed_dim', 48),
    )


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("Test Swin Transformer 3D MONAI pour TiCNet (version corrigée)")
    print("=" * 60)

    cfg = {
        'hidden_dim': 64,
        'dropout': 0.1,
        'nheads': 8,
        'num_queries': 512,
        'dim_feedforward': 256,
        'enc_layers': 6,
        'dec_layers': 6,
        'pre_norm': False,
        'swin_window_size': 2,
        'swin_embed_dim': 48,
    }

    model = build_transformer(cfg)
    model.eval()

    attn_cls = model.swin.layers1[0].blocks[0].attn.__class__.__name__
    print(f"\n[1] Architecture confirmée")
    print(f"    Attention class : {attn_cls}")
    print(f"    embed_dim       : 48  (vs 24 avant)")
    print(f"    pos_embed       : ignoré (Swin utilise relative position bias)")

    print(f"\n[2] Test TRAIN — crop 4×4×4 (cas réel TiCNet)")
    src = torch.randn(2, 64, 4, 4, 4)
    pos = torch.randn(2, 64, 4, 4, 4)   # ignoré par le forward
    with torch.no_grad():
        out = model(src, pos)
    assert out.shape == src.shape, f"Shape mismatch: {out.shape} vs {src.shape}"
    print(f"    (2,64,4,4,4) → {out.shape}  OK")

    print(f"\n[3] Test TEST — tailles variables LUNA16")
    for D, H, W in [(17, 11, 17), (16, 15, 19), (9, 7, 11), (20, 18, 22)]:
        src = torch.randn(1, 64, D, H, W)
        pos = torch.randn(1, 64, D, H, W)
        with torch.no_grad():
            out = model(src, pos)
        assert out.shape == src.shape
        print(f"    ({D:2},{H:2},{W:2}) → {out.shape}  OK")

    print("\n" + "=" * 60)
    print("TOUS LES TESTS PASSÉS")
    print("=" * 60)
