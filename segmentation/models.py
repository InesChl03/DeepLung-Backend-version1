# from django.db import models


# class NoduleSegmentation(models.Model):
#     scan             = models.ForeignKey(
#                            'ctscan.CtScan',
#                            on_delete=models.CASCADE,
#                            related_name='segmentations'
#                        )
#     nodule_id_ticnet = models.IntegerField()
#     rpn_score        = models.FloatField(default=0.0)
#     center_mm        = models.JSONField(default=list)   # ← ajout
#     center_voxel     = models.JSONField(default=list)   # ← ajout
#     diam_ticnet_mm   = models.FloatField(default=0.0)
#     diam_seg_mm      = models.FloatField(default=0.0)
#     volume_mm3       = models.FloatField(default=0.0)
#     n_voxels         = models.IntegerField(default=0)
#     ct_image_path        = models.TextField(blank=True)
#     mask_npy_path        = models.TextField(blank=True)
#     mask_image_path      = models.TextField(blank=True)
#     contour_image_path   = models.TextField(blank=True)
#     mesh_json_path       = models.TextField(blank=True)
#     created_at       = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table       = 'nodule_segmentations'
#         unique_together = ('scan', 'nodule_id_ticnet')

#     def __str__(self):
#         return f"Seg scan={self.scan_id} nodule={self.nodule_id_ticnet}"
from django.db import models


class NoduleSegmentation(models.Model):
    scan             = models.ForeignKey(
                           'ctscan.CtScan',
                           on_delete=models.CASCADE,
                           related_name='segmentations'
                       )
    nodule_id        = models.IntegerField()   # ← identifiant LOCAL (1, 2, 3...) généré par run_inference
    rpn_score        = models.FloatField(default=0.0)
    center_mm        = models.JSONField(default=list)
    center_voxel     = models.JSONField(default=list)
    diam_ticnet_mm   = models.FloatField(default=0.0)
    diam_seg_mm      = models.FloatField(default=0.0)
    volume_mm3       = models.FloatField(default=0.0)
    n_voxels         = models.IntegerField(default=0)
    ct_image_path        = models.TextField(blank=True)
    mask_npy_path        = models.TextField(blank=True)
    mask_image_path      = models.TextField(blank=True)
    contour_image_path   = models.TextField(blank=True)
    mesh_json_path        = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table       = 'nodule_segmentations'
        unique_together = ('scan', 'nodule_id')

    def __str__(self):
        return f"Seg scan={self.scan_id} nodule={self.nodule_id}"