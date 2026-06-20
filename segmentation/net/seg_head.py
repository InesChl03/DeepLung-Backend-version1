"""
seg_head.py  —  Attention U-Net 3D pour la segmentation de nodules pulmonaires
===============================================================================
Basé sur : Attention U-Net (Oktay et al., 2018)
Adapté aux dimensions RÉELLES de TiCNet/FeatureNet.

Dimensions réelles vérifiées expérimentalement :
    features[0] x     : (B,   1, 64, 64, 64)  image originale
    features[1] rev2  : (B, 128,  8,  8,  8)  skip niveau 1 (résolution basse)
    features[2] comb1 : (B, 128, 16, 16, 16)  skip niveau 2 (résolution haute)
    feat_4            : (B,  64, 16, 16, 16)  bottleneck

Décodeur Attention U-Net 3D :

    feat_4  (B, 64, 16, 16, 16)
        │
        ▼  ConvTranspose ×2
    up1 (B, 64, 32, 32, 32)
        │                    ┌─── comb1_up (B,128,32,32,32) [comb1 upsamplé]
        └──→ AttGate1 ───────┘
        │
        ▼  concat(up1, comb1_att) → (B,192,32,32,32)
        DecBlock                  → (B, 64,32,32,32)
        │
        ▼  ConvTranspose ×2
    up2 (B, 64, 64, 64, 64)
        │                    ┌─── rev2_up (B,128,64,64,64) [rev2 upsamplé ×8]
        └──→ AttGate2 ───────┘
        │
        ▼  concat(up2, rev2_att) → (B,192,64,64,64)
        DecBlock                  → (B, 32,64,64,64)
        │
        conv_final → (B, 1, 64, 64, 64)   ← logits
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# ─────────────────────────────────────────────────────────────────────────────
#  Attention Gate 3D
# ─────────────────────────────────────────────────────────────────────────────

class AttentionGate3D(nn.Module):
    """
    Attention Gate 3D (Oktay et al., 2018).

    g : gating signal  — vient du décodeur  (résolution basse)
    x : skip connection — vient de l'encodeur (résolution haute)

    1. Upsampler g à la résolution de x
    2. Projeter g et x dans un espace commun (inter_channels)
    3. Sommer + ReLU → Conv 1×1 + Sigmoid → carte d'attention [0,1]
    4. x_att = x * attention
    """

    def __init__(self, g_channels, x_channels, inter_channels=None):
        super(AttentionGate3D, self).__init__()

        if inter_channels is None:
            inter_channels = max(min(g_channels, x_channels) // 2, 1)

        self.W_g = nn.Sequential(
            nn.Conv3d(g_channels, inter_channels, kernel_size=1, bias=False),
            nn.BatchNorm3d(inter_channels)
        )
        self.W_x = nn.Sequential(
            nn.Conv3d(x_channels, inter_channels, kernel_size=1, bias=False),
            nn.BatchNorm3d(inter_channels)
        )
        self.psi = nn.Sequential(
            nn.Conv3d(inter_channels, 1, kernel_size=1, bias=False),
            nn.BatchNorm3d(1),
            nn.Sigmoid()
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, g, x):
        """
        g : (B, g_channels, Dg, Hg, Wg)
        x : (B, x_channels, Dx, Hx, Wx)
        Retourne x_att et la carte d'attention
        """
        # Upsampler g à la résolution de x
        g_up = F.interpolate(
            g, size=x.shape[2:],
            mode='trilinear', align_corners=False
        )
        g_proj    = self.W_g(g_up)
        x_proj    = self.W_x(x)
        combined  = self.relu(g_proj + x_proj)
        attention = self.psi(combined)
        x_att     = x * attention
        return x_att, attention


# ─────────────────────────────────────────────────────────────────────────────
#  Bloc de décodage double convolution
# ─────────────────────────────────────────────────────────────────────────────

class DecBlock(nn.Module):
    """Conv3d → BN → ReLU → Conv3d → BN → ReLU"""

    def __init__(self, in_channels, out_channels):
        super(DecBlock, self).__init__()
        self.block = nn.Sequential(
            nn.Conv3d(in_channels,  out_channels, kernel_size=3,
                      padding=1, bias=False),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv3d(out_channels, out_channels, kernel_size=3,
                      padding=1, bias=False),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


# ─────────────────────────────────────────────────────────────────────────────
#  Attention U-Net 3D — SegHead complet
# ─────────────────────────────────────────────────────────────────────────────

class SegHead(nn.Module):
    """
    Décodeur Attention U-Net 3D avec les dimensions réelles de TiCNet.

    Dimensions réelles :
        feat_4            : (B,  64, 16, 16, 16)
        features[2] comb1 : (B, 128, 16, 16, 16)
        features[1] rev2  : (B, 128,  8,  8,  8)

    Usage :
        features, feat_4 = model.feature_net(images)
        pred, att_maps   = model.seg_head(feat_4, features)
        # pred : (B, 1, 64, 64, 64)
    """

    def __init__(self):
        super(SegHead, self).__init__()

        # ── Niveau 1 ──────────────────────────────────────────────────────────
        # feat_4 (B,64,16,16,16) → ConvTranspose×2 → up1 (B,64,32,32,32)
        # comb1  (B,128,16,16,16) → Upsample×2 → comb1_up (B,128,32,32,32)
        # AttGate1 : g=up1(64ch), x=comb1_up(128ch)
        # concat(up1, comb1_att) : 64+128=192ch
        # DecBlock : 192 → 64ch
        self.up1       = nn.ConvTranspose3d(64, 64, kernel_size=2, stride=2)
        self.up_comb1  = nn.Upsample(scale_factor=2, mode='trilinear',
                                     align_corners=False)
        self.att1      = AttentionGate3D(g_channels=64, x_channels=128,
                                         inter_channels=32)
        self.dec1      = DecBlock(in_channels=64 + 128, out_channels=64)

        # ── Niveau 2 ──────────────────────────────────────────────────────────
        # dec1  (B,64,32,32,32) → ConvTranspose×2 → up2 (B,64,64,64,64)
        # rev2  (B,128,8,8,8)   → Upsample×8      → rev2_up (B,128,64,64,64)
        # AttGate2 : g=up2(64ch), x=rev2_up(128ch)
        # concat(up2, rev2_att) : 64+128=192ch
        # DecBlock : 192 → 32ch
        self.up2      = nn.ConvTranspose3d(64, 64, kernel_size=2, stride=2)
        self.up_rev2  = nn.Upsample(scale_factor=8, mode='trilinear',
                                    align_corners=False)
        self.att2     = AttentionGate3D(g_channels=64, x_channels=128,
                                        inter_channels=32)
        self.dec2     = DecBlock(in_channels=64 + 128, out_channels=32)

        # ── Couche finale ─────────────────────────────────────────────────────
        # dec2 (B,32,64,64,64) → conv 1×1 → (B,1,64,64,64)
        self.conv_final = nn.Conv3d(32, 1, kernel_size=1)

        # Initialisation des poids
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv3d, nn.ConvTranspose3d)):
                nn.init.kaiming_normal_(m.weight, mode='fan_out',
                                        nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm3d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, feat_4, features):
        """
        feat_4   : (B,  64, 16, 16, 16)
        features : [x, rev2, comb1]
            x     : (B,   1, 64, 64, 64)
            rev2  : (B, 128,  8,  8,  8)
            comb1 : (B, 128, 16, 16, 16)

        Retourne :
            out      : (B, 1, 64, 64, 64)  logits
            att_maps : [att1, att2]         cartes d'attention
        """
        _, rev2, comb1 = features

        # ── Niveau 1 ──────────────────────────────────────────────────────────
        # feat_4 (B,64,16,16,16) → up → (B,64,32,32,32)
        up1 = self.up1(feat_4)                           # (B, 64,32,32,32)

        # comb1 (B,128,16,16,16) → upsample → (B,128,32,32,32)
        comb1_up = self.up_comb1(comb1)                  # (B,128,32,32,32)

        # Ajustement taille si nécessaire
        if up1.shape[2:] != comb1_up.shape[2:]:
            up1 = F.interpolate(up1, size=comb1_up.shape[2:],
                                mode='trilinear', align_corners=False)

        # Attention Gate 1
        comb1_att, att1 = self.att1(g=up1, x=comb1_up)  # (B,128,32,32,32)

        # Concat + décodage
        d1 = torch.cat([up1, comb1_att], dim=1)          # (B,192,32,32,32)
        d1 = self.dec1(d1)                               # (B, 64,32,32,32)

        # ── Niveau 2 ──────────────────────────────────────────────────────────
        # d1 (B,64,32,32,32) → up → (B,64,64,64,64)
        up2 = self.up2(d1)                               # (B, 64,64,64,64)

        # rev2 (B,128,8,8,8) → upsample×8 → (B,128,64,64,64)
        rev2_up = self.up_rev2(rev2)                     # (B,128,64,64,64)

        # Ajustement taille si nécessaire
        if up2.shape[2:] != rev2_up.shape[2:]:
            up2 = F.interpolate(up2, size=rev2_up.shape[2:],
                                mode='trilinear', align_corners=False)

        # Attention Gate 2
        rev2_att, att2 = self.att2(g=up2, x=rev2_up)    # (B,128,64,64,64)

        # Concat + décodage
        d2 = torch.cat([up2, rev2_att], dim=1)           # (B,192,64,64,64)
        d2 = self.dec2(d2)                               # (B, 32,64,64,64)

        # ── Sortie ────────────────────────────────────────────────────────────
        out = self.conv_final(d2)                        # (B,  1,64,64,64)

        return out, [att1, att2]