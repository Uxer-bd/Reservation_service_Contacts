from django.urls import path

from . import views


urlpatterns = [
    path("connexion/", views.connexion, name="connexion"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),
    path("prestataire/profil/", views.profil_prestataire, name="prestataire_profil"),
    path("prestataire/dashboard/", views.dashboard_prestataire, name="dashboard_prestataire"),
    path("prestataire/services/ajouter/", views.service_ajouter, name="service_ajouter"),
    path(
        "prestataire/services/<int:service_id>/modifier/",
        views.service_modifier,
        name="service_modifier",
    ),
    path(
        "prestataire/services/<int:service_id>/supprimer/",
        views.service_supprimer,
        name="service_supprimer",
    ),
    path(
        "prestataire/demandes/<int:reservation_id>/statut/",
        views.demande_modifier_statut,
        name="demande_modifier_statut",
    ),
]
