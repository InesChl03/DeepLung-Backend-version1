from django.db import models
from accounts.models import Doctor


class Patient(models.Model):

    class Sexe(models.TextChoices):
        HOMME = "H", "Homme"
        FEMME = "F", "Femme"

    doctor    = models.ForeignKey(
                    Doctor,
                    on_delete=models.CASCADE,
                    related_name="patients",
                    verbose_name="Médecin responsable"
                )
    nom       = models.CharField(max_length=100, verbose_name="Nom")
    prenom    = models.CharField(max_length=100, verbose_name="Prénom")
    age       = models.PositiveIntegerField(verbose_name="Âge")
    sexe      = models.CharField(max_length=1, choices=Sexe.choices, verbose_name="Sexe")
    telephone = models.CharField(max_length=20, verbose_name="N° Téléphone")
    adresse   = models.TextField(verbose_name="Adresse")
    historique_medical = models.TextField(        # ← AJOUTER
        blank=True,
        default="",
        verbose_name="Historique médical"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nom} {self.prenom}"

    class Meta:
        db_table     = "patients"
        verbose_name = "Patient"
        ordering     = ["-created_at"]