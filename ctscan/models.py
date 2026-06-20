from django.db import models

from django.db import models
from dossiers.models import Dossier


class CtScan(models.Model):
    """
    Un scan CT uploadé par le médecin pour un dossier patient.
    Contient le fichier .mhd + .raw et le résultat de l'analyse TiCNet.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        EN_COURS   = "EN_COURS",   "En cours d'analyse"
        TERMINE    = "TERMINE",    "Terminé"
        ERREUR     = "ERREUR",     "Erreur"

    dossier    = models.ForeignKey(
                     Dossier,
                     on_delete=models.CASCADE,
                     related_name="ctscans",
                     verbose_name="Dossier"
                 )
    fichier_mhd = models.FileField(
                      upload_to="ctscans/%Y/%m/",
                      verbose_name="Fichier .mhd"
                  )
    fichier_raw = models.FileField(
                      upload_to="ctscans/%Y/%m/",
                      verbose_name="Fichier .raw"
                  )
    statut      = models.CharField(
                      max_length=20,
                      choices=Statut.choices,
                      default=Statut.EN_ATTENTE,
                      verbose_name="Statut"
                  )
    # Métadonnées DICOM récupérées au preprocessing
    origin_z    = models.FloatField(null=True, blank=True)
    origin_y    = models.FloatField(null=True, blank=True)
    origin_x    = models.FloatField(null=True, blank=True)
    spacing_z   = models.FloatField(null=True, blank=True)
    spacing_y   = models.FloatField(null=True, blank=True)
    spacing_x   = models.FloatField(null=True, blank=True)
        ##################################
    ebox_z = models.FloatField(null=True, blank=True)
    ebox_y = models.FloatField(null=True, blank=True)
    ebox_x = models.FloatField(null=True, blank=True)

    message_erreur = models.TextField(blank=True, verbose_name="Message d'erreur")
    duree_analyse  = models.FloatField(null=True, blank=True, verbose_name="Durée (secondes)")

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CtScan [{self.statut}] — {self.dossier.patient.nom} {self.dossier.patient.prenom}"

    class Meta:
        db_table     = "ctscans"
        verbose_name = "CT Scan"
        ordering     = ["-created_at"]


class Nodule(models.Model):
    """
    Nodule pulmonaire détecté par TiCNet dans un CT scan.
    Coordonnées en millimètres dans le repère monde ITK.
    """
    ctscan      = models.ForeignKey(
                      CtScan,
                      on_delete=models.CASCADE,
                      related_name="nodules",
                      verbose_name="CT Scan"
                  )
    rang        = models.PositiveIntegerField(verbose_name="Rang (par probabilité)")

    # Coordonnées monde (mm) — repère ITK (z, y, x)
    monde_z     = models.FloatField(verbose_name="Coordonnée monde Z (mm)")
    monde_y     = models.FloatField(verbose_name="Coordonnée monde Y (mm)")
    monde_x     = models.FloatField(verbose_name="Coordonnée monde X (mm)")

    # Coordonnées voxel dans l'image preprocessée
    voxel_z     = models.FloatField(verbose_name="Voxel Z")
    voxel_y     = models.FloatField(verbose_name="Voxel Y")
    voxel_x     = models.FloatField(verbose_name="Voxel X")

    diametre_mm = models.FloatField(verbose_name="Diamètre estimé (mm)")
    probabilite = models.FloatField(verbose_name="Probabilité de malignité")

    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (f"Nodule #{self.rang} — prob={self.probabilite:.2%} "
                f"diam={self.diametre_mm:.1f}mm — {self.ctscan}")

    class Meta:
        db_table     = "nodules"
        verbose_name = "Nodule"
        ordering     = ["ctscan", "rang"]
