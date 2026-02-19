from django import forms

from .models import Reservation


class ReservationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False

    class Meta:
        model = Reservation
        fields = ["nom_client", "tel_client", "description"]
        widgets = {
            "nom_client": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "Jean Dupont",
                    "autocomplete": "name",
                }
            ),
            "tel_client": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "+33 6 12 34 56 78",
                    "autocomplete": "tel",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "input-field textarea-field",
                    "placeholder": "Décrivez votre projet ou le problème à résoudre...",
                    "rows": 4,
                }
            ),
        }
        labels = {
            "nom_client": "Nom complet",
            "tel_client": "Numéro de téléphone",
            "description": "Description de vos besoins",
        }
