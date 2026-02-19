from django.contrib import admin
from django import forms

from .models import Avis, Prestataire, Reservation, Service, TypeService
# Register your models here.


class ServiceAdminForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["prestataire", "type_service", "description", "prix", "publier", "adresse", "image"]

    def clean_type_service(self):
        type_service = self.cleaned_data.get("type_service")
        if not type_service:
            raise forms.ValidationError("Veuillez choisir un type de service.")
        return type_service


class TypeServiceAdmin(admin.ModelAdmin):
    list_display = ("nom", "actif")
    list_filter = ("actif",)
    search_fields = ("nom",)
    list_editable = ("actif",)


class PrestataireAdmin(admin.ModelAdmin):
    list_display = ("nom_complet_affichage", "nom_entreprise", "user", "telephone", "adresse")
    list_filter = ('adresse',)
    search_fields = (
        "nom_entreprise",
        "adresse",
        "user__first_name",
        "user__last_name",
        "user__username",
    )
    list_select_related = ("user",)

    @admin.display(description="Nom complet", ordering="user__last_name")
    def nom_complet_affichage(self, obj):
        return obj.nom_complet

class ServiceAdmin(admin.ModelAdmin):
    form = ServiceAdminForm
    list_display = ('nom_affichage', 'type_service', 'prestataire', 'prix', 'publier')
    list_filter = ('publier', 'adresse', 'type_service')
    search_fields = ('nom_service', 'type_service__nom', 'description',)
    list_editable = ('publier',)

class ReservationAdmin(admin.ModelAdmin):
    list_display = ("service", "nom_client", "tel_client", "status")
    list_filter = ("status", "service__type_service")
    search_fields = ("service__nom_service", "service__type_service__nom", "nom_client", "tel_client")
    list_editable = ("status",)


class AvisAdmin(admin.ModelAdmin):
    list_display = ("service", "nom_client", "note", "visible", "date_creation")
    list_filter = ("visible", "note", "service__type_service")
    search_fields = ("service__nom_service", "service__type_service__nom", "nom_client", "commentaire")
    list_editable = ("visible",)


admin.site.register(TypeService, TypeServiceAdmin)
admin.site.register(Prestataire, PrestataireAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Avis, AvisAdmin)
