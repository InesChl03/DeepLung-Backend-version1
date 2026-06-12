# import copy
# from typing import Optional, List

# from ticnet.ticnet_config import train_config as cfg
# import torch
# import torch.nn.functional as F
# from torch import nn, Tensor


# class Transformer(nn.Module):

#     def __init__(
#         self, 
#         d_model: int = 512, 
#         nhead: int = 8, 
#         num_queries: int = 100, 
#         num_encoder_layers: int = 6,
#         num_decoder_layers: int = 6, 
#         dim_feedforward: int = 2048, 
#         dropout: float = 0.1,
#         activation: str = "relu", 
#         normalize_before: bool = False,
#         return_intermediate_dec: bool = False
#     ):
#         super().__init__()
#         self.d_model = d_model

#         encoder_layer = TransformerEncoderLayer(
#             d_model, 
#             nhead, 
#             dim_feedforward,
#             dropout, 
#             activation, 
#             normalize_before
#         )
#         encoder_norm = nn.LayerNorm(d_model) if normalize_before else None
#         self.encoder = TransformerEncoder(
#             encoder_layer, 
#             num_encoder_layers, 
#             encoder_norm
#         )

#         decoder_layer = TransformerDecoderLayer(
#             d_model, 
#             nhead, 
#             dim_feedforward,
#             dropout, 
#             activation, 
#             normalize_before
#         )
#         decoder_norm = nn.LayerNorm(d_model)
#         self.decoder = TransformerDecoder(
#             decoder_layer, 
#             num_decoder_layers, 
#             decoder_norm,
#             return_intermediate=return_intermediate_dec
#         )
#         self._reset_parameters()
#         self.query_embed = nn.Embedding(num_queries, d_model)
#         self.d_model = d_model
#         self.nhead = nhead

#     def _reset_parameters(self):
#         for p in self.parameters():
#             if p.dim() > 1:
#                 nn.init.xavier_uniform_(p)

#     def forward(self, src, pos_embed):
#         # flatten NxCxHxW to HWxNxC
#         bs, c, d, h, w = src.shape
#         self.query_embed = nn.Embedding(d * h * w, self.d_model)
#         query_embed = self.query_embed.weight.to(src.device)

#         src = src.flatten(2).permute(2, 0, 1)
#         pos_embed = pos_embed.flatten(2).permute(2, 0, 1)
#         query_embed = query_embed.unsqueeze(
#             1).repeat(1, bs, 1)  # [100, 2, 256]
#         mask = torch.zeros(bs, d * h * w).to(src.device)

#         tgt = torch.zeros_like(query_embed)
#         memory = self.encoder(src, src_key_padding_mask=mask,
#                               pos=pos_embed)  # [4096, 2, 256]
#         hs = self.decoder(tgt, memory, memory_key_padding_mask=mask,
#                           pos=pos_embed, query_pos=query_embed)[-1]
#         return hs.view(bs, c, d, h, w)


# class TransformerEncoder(nn.Module):

#     def __init__(self, encoder_layer, num_layers, norm=None):
#         super().__init__()
#         self.layers = _get_clones(encoder_layer, num_layers)
#         self.num_layers = num_layers
#         self.norm = norm

#     def forward(self, src,
#                 mask: Optional[Tensor] = None,
#                 src_key_padding_mask: Optional[Tensor] = None,
#                 pos: Optional[Tensor] = None):
#         output = src

#         for layer in self.layers:
#             output = layer(output, src_mask=mask,
#                            src_key_padding_mask=src_key_padding_mask, pos=pos)

#         if self.norm is not None:
#             output = self.norm(output)

#         return output


# class TransformerDecoder(nn.Module):

#     def __init__(self, decoder_layer, num_layers, norm=None, return_intermediate=False):
#         super().__init__()
#         self.layers = _get_clones(decoder_layer, num_layers)
#         self.num_layers = num_layers
#         self.norm = norm
#         self.return_intermediate = return_intermediate

#     def forward(self, tgt, memory,
#                 tgt_mask: Optional[Tensor] = None,
#                 memory_mask: Optional[Tensor] = None,
#                 tgt_key_padding_mask: Optional[Tensor] = None,
#                 memory_key_padding_mask: Optional[Tensor] = None,
#                 pos: Optional[Tensor] = None,
#                 query_pos: Optional[Tensor] = None):
#         output = tgt

#         intermediate = []

#         for layer in self.layers:
#             output = layer(output, memory, tgt_mask=tgt_mask,
#                            memory_mask=memory_mask,
#                            tgt_key_padding_mask=tgt_key_padding_mask,
#                            memory_key_padding_mask=memory_key_padding_mask,
#                            pos=pos, query_pos=query_pos)
#             if self.return_intermediate:
#                 intermediate.append(self.norm(output))

#         if self.norm is not None:
#             output = self.norm(output)
#             if self.return_intermediate:
#                 intermediate.pop()
#                 intermediate.append(output)

#         if self.return_intermediate:
#             return torch.stack(intermediate)

#         return output.unsqueeze(0)


# class TransformerEncoderLayer(nn.Module):

#     def __init__(self, d_model, nhead, dim_feedforward=2048, dropout=0.1,
#                  activation="relu", normalize_before=False):
#         super().__init__()
#         self.self_attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout)
#         # Implementation of Feedforward model
#         self.linear1 = nn.Linear(d_model, dim_feedforward)
#         self.dropout = nn.Dropout(dropout)
#         self.linear2 = nn.Linear(dim_feedforward, d_model)

#         self.norm1 = nn.LayerNorm(d_model)
#         self.norm2 = nn.LayerNorm(d_model)
#         self.dropout1 = nn.Dropout(dropout)
#         self.dropout2 = nn.Dropout(dropout)

#         self.activation = _get_activation_fn(activation)
#         self.normalize_before = normalize_before

#     def with_pos_embed(self, tensor, pos: Optional[Tensor]):
#         return tensor if pos is None else tensor + pos

#     def forward_post(self,
#                      src,
#                      src_mask: Optional[Tensor] = None,
#                      src_key_padding_mask: Optional[Tensor] = None,
#                      pos: Optional[Tensor] = None):
#         q = k = self.with_pos_embed(src, pos)

#         src2 = self.self_attn(q, k, value=src, attn_mask=src_mask,
#                               key_padding_mask=src_key_padding_mask)[0]
#         src = src + self.dropout1(src2)
#         src = self.norm1(src)
#         src2 = self.linear2(self.dropout(self.activation(self.linear1(src))))
#         src = src + self.dropout2(src2)
#         src = self.norm2(src)
#         return src

#     def forward_pre(self, src,
#                     src_mask: Optional[Tensor] = None,
#                     src_key_padding_mask: Optional[Tensor] = None,
#                     pos: Optional[Tensor] = None):
#         src2 = self.norm1(src)
#         q = k = self.with_pos_embed(src2, pos)
#         src2 = self.self_attn(q, k, value=src2, attn_mask=src_mask,
#                               key_padding_mask=src_key_padding_mask)[0]
#         src = src + self.dropout1(src2)
#         src2 = self.norm2(src)
#         src2 = self.linear2(self.dropout(self.activation(self.linear1(src2))))
#         src = src + self.dropout2(src2)
#         return src

#     def forward(self, src,
#                 src_mask: Optional[Tensor] = None,
#                 src_key_padding_mask: Optional[Tensor] = None,
#                 pos: Optional[Tensor] = None):
#         if self.normalize_before:
#             return self.forward_pre(src, src_mask, src_key_padding_mask, pos)
#         return self.forward_post(src, src_mask, src_key_padding_mask, pos)


# class TransformerDecoderLayer(nn.Module):

#     def __init__(self, d_model, nhead, dim_feedforward=2048, dropout=0.1,
#                  activation="relu", normalize_before=False):
#         super().__init__()
#         self.self_attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout)
#         self.multihead_attn = nn.MultiheadAttention(
#             d_model, nhead, dropout=dropout)
#         # Implementation of Feedforward model
#         self.linear1 = nn.Linear(d_model, dim_feedforward)
#         self.dropout = nn.Dropout(dropout)
#         self.linear2 = nn.Linear(dim_feedforward, d_model)

#         self.norm1 = nn.LayerNorm(d_model)
#         self.norm2 = nn.LayerNorm(d_model)
#         self.norm3 = nn.LayerNorm(d_model)
#         self.dropout1 = nn.Dropout(dropout)
#         self.dropout2 = nn.Dropout(dropout)
#         self.dropout3 = nn.Dropout(dropout)

#         self.activation = _get_activation_fn(activation)
#         self.normalize_before = normalize_before

#     def with_pos_embed(self, tensor, pos: Optional[Tensor]):
#         return tensor if pos is None else tensor + pos

#     def forward_post(self, tgt, memory,
#                      tgt_mask: Optional[Tensor] = None,
#                      memory_mask: Optional[Tensor] = None,
#                      tgt_key_padding_mask: Optional[Tensor] = None,
#                      memory_key_padding_mask: Optional[Tensor] = None,
#                      pos: Optional[Tensor] = None,
#                      query_pos: Optional[Tensor] = None):
#         q = k = self.with_pos_embed(tgt, query_pos)
#         tgt2 = self.self_attn(q, k, value=tgt, attn_mask=tgt_mask,
#                               key_padding_mask=tgt_key_padding_mask)[0]
#         tgt = tgt + self.dropout1(tgt2)
#         tgt = self.norm1(tgt)
#         tgt2 = self.multihead_attn(query=self.with_pos_embed(tgt, query_pos),
#                                    key=self.with_pos_embed(memory, pos),
#                                    value=memory, attn_mask=memory_mask,
#                                    key_padding_mask=memory_key_padding_mask)[0]
#         tgt = tgt + self.dropout2(tgt2)
#         tgt = self.norm2(tgt)
#         tgt2 = self.linear2(self.dropout(self.activation(self.linear1(tgt))))
#         tgt = tgt + self.dropout3(tgt2)
#         tgt = self.norm3(tgt)
#         return tgt

#     def forward_pre(self, tgt, memory,
#                     tgt_mask: Optional[Tensor] = None,
#                     memory_mask: Optional[Tensor] = None,
#                     tgt_key_padding_mask: Optional[Tensor] = None,
#                     memory_key_padding_mask: Optional[Tensor] = None,
#                     pos: Optional[Tensor] = None,
#                     query_pos: Optional[Tensor] = None):
#         tgt2 = self.norm1(tgt)
#         q = k = self.with_pos_embed(tgt2, query_pos)
#         tgt2 = self.self_attn(q, k, value=tgt2, attn_mask=tgt_mask,
#                               key_padding_mask=tgt_key_padding_mask)[0]
#         tgt = tgt + self.dropout1(tgt2)
#         tgt2 = self.norm2(tgt)
#         tgt2 = self.multihead_attn(query=self.with_pos_embed(tgt2, query_pos),
#                                    key=self.with_pos_embed(memory, pos),
#                                    value=memory, attn_mask=memory_mask,
#                                    key_padding_mask=memory_key_padding_mask)[0]
#         tgt = tgt + self.dropout2(tgt2)
#         tgt2 = self.norm3(tgt)
#         tgt2 = self.linear2(self.dropout(self.activation(self.linear1(tgt2))))
#         tgt = tgt + self.dropout3(tgt2)
#         return tgt

#     def forward(self, tgt, memory,
#                 tgt_mask: Optional[Tensor] = None,
#                 memory_mask: Optional[Tensor] = None,
#                 tgt_key_padding_mask: Optional[Tensor] = None,
#                 memory_key_padding_mask: Optional[Tensor] = None,
#                 pos: Optional[Tensor] = None,
#                 query_pos: Optional[Tensor] = None):
#         if self.normalize_before:
#             return self.forward_pre(tgt, memory, tgt_mask, memory_mask,
#                                     tgt_key_padding_mask, memory_key_padding_mask, pos, query_pos)
#         return self.forward_post(tgt, memory, tgt_mask, memory_mask,
#                                  tgt_key_padding_mask, memory_key_padding_mask, pos, query_pos)


# def _get_clones(module, N):
#     return nn.ModuleList([copy.deepcopy(module) for i in range(N)])


# def build_transformer(cfg):
#     return Transformer(
#         d_model=cfg['hidden_dim'],
#         dropout=cfg['dropout'],
#         nhead=cfg['nheads'],
#         num_queries=cfg['num_queries'],
#         dim_feedforward=cfg['dim_feedforward'],
#         num_encoder_layers=cfg['enc_layers'],
#         num_decoder_layers=cfg['dec_layers'],
#         normalize_before=cfg['pre_norm'],
#         return_intermediate_dec=True,
#     )


# def _get_activation_fn(activation):
#     """Return an activation function given a string"""
#     if activation == "relu":
#         return F.relu
#     if activation == "gelu":
#         return F.gelu
#     if activation == "glu":
#         return F.glu
#     raise RuntimeError(F"activation should be relu/gelu, not {activation}.")
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
