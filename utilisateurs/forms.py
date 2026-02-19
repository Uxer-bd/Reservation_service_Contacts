from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from services.models import Prestataire, Service, TypeService


class UtilisateurRegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)


class PrestataireForm(forms.ModelForm):
    class Meta:
        model = Prestataire
        fields = ["nom_entreprise", "adresse", "telephone", "photo_profil"]
        widgets = {
            "nom_entreprise": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nom de l'entreprise"}
            ),
            "adresse": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Adresse"}
            ),
            "telephone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Numero de telephone"}
            ),
            "photo_profil": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
            ),
        }


class ServiceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type_service"].queryset = TypeService.objects.filter(
            actif=True
        ).order_by("nom")
        self.fields["type_service"].empty_label = "Choisir un type de service"

    def clean_type_service(self):
        type_service = self.cleaned_data.get("type_service")
        if not type_service:
            raise forms.ValidationError("Veuillez choisir un type de service.")
        return type_service

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.type_service_id:
            instance.nom_service = instance.type_service.nom
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Service
        fields = ["type_service", "description", "prix", "publier", "adresse", "image"]
        widgets = {
            "type_service": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Description du service",
                }
            ),
            "prix": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Prix"}
            ),
            "publier": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "adresse": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Adresse du service"}
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        }
        labels = {
            "type_service": "Type de service",
        }
