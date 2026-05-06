from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN  = "ADMIN",  "Admin"
        DOCTOR = "DOCTOR", "Doctor"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.DOCTOR,
    )

    # email existe déjà dans AbstractUser — on ne touche à rien
    REQUIRED_FIELDS = []

    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    def is_admin(self):
        return self.role == self.Role.ADMIN

    class Meta:
        db_table     = "users"
        verbose_name = "User"


class Doctor(models.Model):
    user           = models.OneToOneField(
                         User,
                         on_delete=models.CASCADE,
                         related_name="doctor_profile"
                     )
    full_name      = models.CharField(max_length=200,  verbose_name="Nom complet")
    license_number = models.CharField(max_length=50, unique=True, verbose_name="ID Professionnel")
    hospital       = models.CharField(max_length=200,  verbose_name="Nom de l'établissement")

    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.full_name} — {self.license_number}"

    class Meta:
        db_table     = "doctors"
        verbose_name = "Doctor"