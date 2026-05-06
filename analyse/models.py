from django.db import models
from dossiers.models import Dossier, FichierMedical


class Analyse(models.Model):
    """
    Résultat d'une analyse IA sur un fichier médical du dossier.
    """
    class Statut(models.TextChoices):
        EN_ATTENTE  = "EN_ATTENTE",  "En attente"
        EN_COURS    = "EN_COURS",    "En cours"
        TERMINE     = "TERMINE",     "Terminé"
        ECHOUE      = "ECHOUE",      "Échoué"

    dossier         = models.ForeignKey(
                          Dossier,
                          on_delete=models.CASCADE,
                          related_name="analyses",
                          verbose_name="Dossier"
                      )
    fichier_medical = models.ForeignKey(
                          FichierMedical,
                          on_delete=models.CASCADE,
                          related_name="analyses",
                          verbose_name="Fichier analysé"
                      )
    statut          = models.CharField(
                          max_length=15,
                          choices=Statut.choices,
                          default=Statut.EN_ATTENTE,
                          verbose_name="Statut"
                      )
    nodule_count    = models.PositiveIntegerField(default=0, verbose_name="Nombre de nodules")
    max_probability = models.FloatField(default=0.0,  verbose_name="Probabilité max")
    niveau_risque   = models.CharField(max_length=20, blank=True, verbose_name="Niveau de risque")
    slices_dir      = models.CharField(max_length=500, blank=True, verbose_name="Dossier slices")
    erreur          = models.TextField(blank=True, verbose_name="Message d'erreur")
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analyse #{self.pk} — {self.dossier.patient.nom} [{self.get_statut_display()}]"

    class Meta:
        db_table     = "analyses"
        verbose_name = "Analyse"
        ordering     = ["-created_at"]


class Nodule(models.Model):
    """
    Un nodule détecté lors d'une analyse.
    """
    class Risque(models.TextChoices):
        FAIBLE   = "FAIBLE",   "Faible"
        MODERE   = "MODERE",   "Modéré"
        ELEVE    = "ELEVE",    "Élevé"
        CRITIQUE = "CRITIQUE", "Critique"

    analyse     = models.ForeignKey(
                      Analyse,
                      on_delete=models.CASCADE,
                      related_name="nodules",
                      verbose_name="Analyse"
                  )
    coordX      = models.FloatField(verbose_name="Coordonnée X")
    coordY      = models.FloatField(verbose_name="Coordonnée Y")
    coordZ      = models.FloatField(verbose_name="Coordonnée Z")
    diameter_mm = models.FloatField(verbose_name="Diamètre (mm)")
    probability = models.FloatField(verbose_name="Probabilité de malignité")
    risk        = models.CharField(
                      max_length=10,
                      choices=Risque.choices,
                      verbose_name="Niveau de risque"
                  )

    def __str__(self):
        return f"Nodule {self.diameter_mm}mm — prob {self.probability:.2%}"

    class Meta:
        db_table     = "nodules"
        verbose_name = "Nodule"
        ordering     = ["-probability"]