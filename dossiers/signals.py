from django.db.models.signals import post_save
from django.dispatch import receiver
from patients.models import Patient
from .models import Dossier, Rapport


@receiver(post_save, sender=Patient)
def create_dossier_for_patient(sender, instance, created, **kwargs):
    """
    Dès qu'un patient est créé → crée automatiquement
    son dossier et son rapport vide.
    """
    if created:
        dossier = Dossier.objects.create(patient=instance)
        Rapport.objects.create(dossier=dossier)