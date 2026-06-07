from django.db import models
from patients.models import Patient


class Dossier(models.Model):
    """
    Chaque patient a un seul dossier médical.
    Créé automatiquement à la création du patient.
    """
    patient    = models.OneToOneField(
                     Patient,
                     on_delete=models.CASCADE,
                     related_name="dossier",
                     verbose_name="Patient"
                 )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dossier de {self.patient.nom} {self.patient.prenom}"

    class Meta:
        db_table     = "dossiers"
        verbose_name = "Dossier"


class FichierMedical(models.Model):
    """
    Fichiers uploadés dans le dossier du patient.
    Peut être une image CT, X-Ray ou autre.
    """
    class TypeFichier(models.TextChoices):
        CT_SCAN = "CT",     "CT Scan"
        XRAY    = "XRAY",   "Radio X-Ray"
        AUTRE   = "AUTRE",  "Autre"

    dossier     = models.ForeignKey(
                      Dossier,
                      on_delete=models.CASCADE,
                      related_name="fichiers",
                      verbose_name="Dossier"
                  )
    type_fichier = models.CharField(
                       max_length=10,
                       choices=TypeFichier.choices,
                       verbose_name="Type de fichier"
                   )
    fichier      = models.FileField(
                       upload_to="dossiers/%Y/%m/",
                       verbose_name="Fichier"
                   )
    description  = models.CharField(max_length=255, blank=True, verbose_name="Description")
    uploaded_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_fichier_display()} — {self.dossier.patient.nom}"

    class Meta:
        db_table     = "fichiers_medicaux"
        verbose_name = "Fichier Médical"
        ordering     = ["-uploaded_at"]


class Rapport(models.Model):
    """
    Rapport détaillé qui résume tous les résultats du patient.
    Un seul rapport par dossier.
    """
    class Statut(models.TextChoices):
        EN_ATTENTE  = "EN_ATTENTE",  "En attente d'analyse"
        ANALYSE     = "ANALYSE",     "Analysé"
        FINALISE    = "FINALISE",    "Finalisé"

    dossier          = models.OneToOneField(
                           Dossier,
                           on_delete=models.CASCADE,
                           related_name="rapport",
                           verbose_name="Dossier"
                       )
    statut           = models.CharField(
                           max_length=20,
                           choices=Statut.choices,
                           default=Statut.EN_ATTENTE,
                           verbose_name="Statut"
                       )
    resultat_ia      = models.TextField(blank=True, verbose_name="Résultat IA")
    notes_medecin    = models.TextField(blank=True, verbose_name="Notes du médecin")
    conclusion       = models.TextField(blank=True, verbose_name="Conclusion")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rapport — {self.dossier.patient.nom} [{self.get_statut_display()}]"

    class Meta:
        db_table     = "rapports"
        verbose_name = "Rapport"