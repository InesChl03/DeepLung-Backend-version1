from django.db import models
from ctscan.models import CtScan  # ← CtScan (pas CTScan)


class NoduleClassification(models.Model):
    """
    Résultat de classification ResNet50-SWS pour un nodule détecté par TiCNet.
    Créé automatiquement après chaque analyse TiCNet réussie.
    """

    LABEL_CHOICES = [
        (0, "Benigne"),
        (1, "Maligne"),
    ]

    scan             = models.ForeignKey(
                           CtScan,
                           on_delete=models.CASCADE,
                           related_name="classifications"
                       )
    nodule_id_ticnet = models.IntegerField(
                           help_text="ID du nodule dans la table Nodule"
                       )
    rang             = models.PositiveIntegerField()

    # Coordonnées recopiées depuis Nodule pour traçabilité
    voxel_x          = models.FloatField()
    voxel_y          = models.FloatField()
    voxel_z          = models.FloatField()
    diametre_mm      = models.FloatField(null=True, blank=True)
    prob_detection   = models.FloatField(
                           null=True, blank=True,
                           help_text="Probabilité TiCNet (champ 'probabilite')"
                       )

    # Résultat classification ResNet50-SWS
    label            = models.IntegerField(choices=LABEL_CHOICES)
    proba_maligne    = models.FloatField()
    proba_benigne    = models.FloatField()

    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table      = "nodule_classifications"
        ordering      = ["scan", "rang"]
        unique_together = ["scan", "nodule_id_ticnet"]

    def __str__(self):
        return (
            f"Scan {self.scan_id} | Nodule #{self.rang} | "
            f"{self.get_label_display()} ({self.proba_maligne:.2%})"
        )