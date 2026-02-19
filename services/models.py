from django.db import models
from django.contrib.auth.models import User
# Create your models here.


class TypeService(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "type de service"
        verbose_name_plural = "types de service"

    def __str__(self):
        return self.nom


class Prestataire(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nom_entreprise = models.CharField(max_length=100)
    adresse = models.CharField(max_length=255)
    telephone = models.CharField(max_length=20)
    photo_profil = models.ImageField(upload_to="prestataires/profils/", null=True, blank=True)

    @property
    def nom_complet(self):
        full_name = self.user.get_full_name().strip()
        if full_name:
            return full_name
        if self.nom_entreprise:
            return self.nom_entreprise
        return self.user.username

    def __str__(self):
        return self.nom_complet
    
class Service(models.Model):
    prestataire = models.ForeignKey(Prestataire, on_delete=models.CASCADE)
    type_service = models.ForeignKey(
        TypeService, on_delete=models.PROTECT, related_name="services", null=True, blank=True
    )
    nom_service = models.CharField(max_length=100)
    description = models.TextField()
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    publier = models.BooleanField(default=False)
    adresse = models.CharField(max_length=255)
    image = models.ImageField(upload_to='services/images/', null=True, blank=True)

    @property
    def nom_affichage(self):
        if self.type_service_id:
            return self.type_service.nom
        return self.nom_service

    def save(self, *args, **kwargs):
        if self.type_service_id:
            self.nom_service = self.type_service.nom
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom_affichage} - {self.prestataire.nom_complet}"


class Avis(models.Model):
    NOTE_CHOICES = [(i, f"{i}/5") for i in range(1, 6)]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="avis")
    nom_client = models.CharField(max_length=120)
    note = models.PositiveSmallIntegerField(choices=NOTE_CHOICES)
    commentaire = models.TextField(blank=True)
    visible = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "avis"
        verbose_name_plural = "avis"

    def __str__(self):
        return f"Avis {self.note}/5 - {self.service.nom_affichage}"


class Reservation(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    nom_client = models.CharField(max_length=120)
    tel_client = models.CharField(max_length=20)
    description = models.TextField()
    status = models.CharField(max_length=50, default='En attente')

    def __str__(self):
        return f"Reservation pour {self.service.nom_affichage} par {self.nom_client}"
