import unicodedata

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from services.models import Prestataire, Reservation, Service

from .forms import PrestataireForm, ServiceForm


STATUS_OPTIONS = ("En attente", "En cours", "Terminee", "Annulee")
STATUS_VARIANTS = {
    "En attente": ("En attente", "Attente"),
    "En cours": ("En cours", "Encours"),
    "Terminee": ("Terminee", "Termine", "Terminees", "Terminée", "Terminées"),
    "Annulee": ("Annulee", "Annule", "Annulees", "Annules", "Annulée", "Annulées"),
}
STATUS_CLASS_MAP = {
    "En attente": "status-waiting",
    "En cours": "status-progress",
    "Terminee": "status-done",
    "Annulee": "status-cancelled",
}


def _normalize_text(value):
    cleaned = unicodedata.normalize("NFKD", value or "")
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    return " ".join(cleaned.lower().split())


def _canonical_status(value):
    normalized = _normalize_text(value)
    for label, variants in STATUS_VARIANTS.items():
        for variant in variants:
            if normalized == _normalize_text(variant):
                return label
    return ""


def _status_filter_query(status_label):
    variants = STATUS_VARIANTS.get(status_label, ())
    query = Q()
    for variant in variants:
        query |= Q(status__iexact=variant)
    return query


def _get_prestataire(user):
    return Prestataire.objects.filter(user=user).first()


def connexion(request):
    if request.user.is_authenticated:
        return redirect("dashboard_prestataire")

    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if next_url and not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = ""

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Connexion reussie.")
        if next_url:
            return redirect(next_url)
        return redirect("dashboard_prestataire")

    return render(request, "utilisateurs/connexion.html", {"form": form, "next": next_url})


@login_required
def deconnexion(request):
    logout(request)
    messages.info(request, "Vous etes deconnecte.")
    return redirect("connexion")


@login_required
def profil_prestataire(request):
    prestataire = _get_prestataire(request.user)

    if request.method == "POST":
        form = PrestataireForm(request.POST, request.FILES, instance=prestataire)
        if form.is_valid():
            profil = form.save(commit=False)
            profil.user = request.user
            profil.save()
            messages.success(request, "Votre profil prestataire est enregistre.")
            return redirect("dashboard_prestataire")
    else:
        form = PrestataireForm(instance=prestataire)

    context = {
        "form": form,
        "has_profile": bool(prestataire),
    }
    return render(request, "utilisateurs/profil_prestataire_form.html", context)


@login_required
def dashboard_prestataire(request):
    prestataire = _get_prestataire(request.user)
    if not prestataire:
        messages.info(
            request,
            "Completez d'abord votre profil prestataire pour gerer vos services.",
        )
        return redirect("prestataire_profil")

    services_qs = (
        Service.objects.filter(prestataire=prestataire)
        .select_related("type_service")
        .order_by("-id")
    )
    demandes_base_qs = (
        Reservation.objects.filter(service__prestataire=prestataire)
        .select_related("service", "service__type_service")
        .order_by("-id")
    )

    selected_service = request.GET.get("service", "").strip()
    selected_status = _canonical_status(request.GET.get("status", ""))

    demandes_qs = demandes_base_qs
    if selected_service.isdigit():
        service_id = int(selected_service)
        if services_qs.filter(id=service_id).exists():
            demandes_qs = demandes_qs.filter(service_id=service_id)
        else:
            selected_service = ""
    else:
        selected_service = ""

    if selected_status:
        demandes_qs = demandes_qs.filter(_status_filter_query(selected_status))

    demandes_rows = []
    for demande in demandes_qs:
        status_label = _canonical_status(demande.status) or "En attente"
        demandes_rows.append(
            {
                "demande": demande,
                "status": status_label,
                "status_class": STATUS_CLASS_MAP.get(status_label, "status-waiting"),
            }
        )

    stats = {
        "services_total": services_qs.count(),
        "services_publies": services_qs.filter(publier=True).count(),
        "demandes_total": demandes_base_qs.count(),
        "attente": demandes_base_qs.filter(_status_filter_query("En attente")).count(),
        "encours": demandes_base_qs.filter(_status_filter_query("En cours")).count(),
    }

    context = {
        "prestataire": prestataire,
        "services": services_qs,
        "demandes_rows": demandes_rows,
        "status_options": STATUS_OPTIONS,
        "selected_service": selected_service,
        "selected_status": selected_status,
        "stats": stats,
    }
    return render(request, "utilisateurs/dashboard_prestataire.html", context)


@login_required
def service_ajouter(request):
    prestataire = _get_prestataire(request.user)
    if not prestataire:
        messages.info(request, "Completez votre profil prestataire avant d'ajouter un service.")
        return redirect("prestataire_profil")

    form = ServiceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        service = form.save(commit=False)
        service.prestataire = prestataire
        service.save()
        messages.success(request, "Service ajoute avec succes.")
        return redirect("dashboard_prestataire")

    return render(
        request,
        "utilisateurs/service_form.html",
        {"form": form, "title": "Ajouter un service", "submit_label": "Enregistrer"},
    )


@login_required
def service_modifier(request, service_id):
    prestataire = _get_prestataire(request.user)
    if not prestataire:
        messages.info(request, "Completez votre profil prestataire avant de modifier un service.")
        return redirect("prestataire_profil")

    service = get_object_or_404(Service, id=service_id, prestataire=prestataire)
    form = ServiceForm(request.POST or None, request.FILES or None, instance=service)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Service modifie avec succes.")
        return redirect("dashboard_prestataire")

    return render(
        request,
        "utilisateurs/service_form.html",
        {"form": form, "title": "Modifier le service", "submit_label": "Mettre a jour"},
    )


@login_required
def service_supprimer(request, service_id):
    prestataire = _get_prestataire(request.user)
    if not prestataire:
        messages.info(request, "Completez votre profil prestataire avant de supprimer un service.")
        return redirect("prestataire_profil")

    service = get_object_or_404(Service, id=service_id, prestataire=prestataire)
    if request.method == "POST":
        service.delete()
        messages.success(request, "Service supprime avec succes.")
        return redirect("dashboard_prestataire")

    return render(request, "utilisateurs/service_confirm_delete.html", {"service": service})


@login_required
def demande_modifier_statut(request, reservation_id):
    prestataire = _get_prestataire(request.user)
    if not prestataire:
        messages.info(request, "Completez votre profil prestataire pour gerer les demandes.")
        return redirect("prestataire_profil")

    demande = get_object_or_404(
        Reservation.objects.select_related("service"),
        id=reservation_id,
        service__prestataire=prestataire,
    )

    if request.method == "POST":
        nouveau_statut = _canonical_status(request.POST.get("status", ""))
        if not nouveau_statut:
            messages.error(request, "Statut invalide.")
        else:
            demande.status = nouveau_statut
            demande.save(update_fields=["status"])
            messages.success(request, "Statut de la demande mis a jour.")

    return redirect("dashboard_prestataire")
