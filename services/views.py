import unicodedata

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ReservationForm
from .models import Avis, Reservation, Service


STATUS_LABELS = ("En attente", "En cours", "Terminee", "Annulee")
STATUS_VARIANTS = {
    "En attente": ("En attente", "Attente"),
    "En cours": ("En cours", "Encours"),
    "Terminee": ("Terminee", "Termine", "Terminees", "Terminée", "Terminées", "Complete", "Complet"),
    "Annulee": ("Annulee", "Annule", "Annulees", "Annules", "Annulée", "Annulées", "Cancel", "Cancelled"),
}
STATUS_CLASS_MAP = {
    "En attente": "status-waiting",
    "En cours": "status-progress",
    "Terminee": "status-done",
    "Annulee": "status-cancelled",
}
PRIORITY_CLASS_MAP = {
    "Haute": "priority-high",
    "Moyenne": "priority-medium",
    "Basse": "priority-low",
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


def _infer_priority(reservation):
    text = _normalize_text(reservation.description)
    status = _canonical_status(reservation.status)
    urgent_terms = ("urgent", "danger", "panne", "fuite", "immediat", "immediate")
    low_terms = ("devis", "information", "renseignement", "question")
    if status == "En attente" and any(term in text for term in urgent_terms):
        return "Haute"
    if any(term in text for term in low_terms) or len(text) < 35:
        return "Basse"
    if status == "En cours":
        return "Moyenne"
    if status == "Terminee":
        return "Basse"
    return "Moyenne"


def accueil(request):
    services = Service.objects.filter(publier=True).select_related(
        "prestataire", "prestataire__user", "type_service"
    )
    query = request.GET.get("q")
    # Keep backward compatibility with older links that used "adresse".
    lieu = request.GET.get("lieu") or request.GET.get("adresse")

    if query:
        services = services.filter(
            Q(nom_service__icontains=query)
            | Q(type_service__nom__icontains=query)
            | Q(description__icontains=query)
        ).distinct()

    if lieu:
        services = services.filter(Q(adresse__icontains=lieu)).distinct()

    # Keep one card per category on homepage; clicking it opens the suggested profile.
    ordered_services = list(services.order_by("type_service__nom", "nom_service", "id"))
    categories = []
    seen_categories = set()
    profile_count_by_category = {}

    for service in ordered_services:
        category_key = (
            f"type:{service.type_service_id}"
            if service.type_service_id
            else f"legacy:{service.nom_service.strip().lower()}"
        )
        profile_count_by_category[category_key] = (
            profile_count_by_category.get(category_key, 0) + 1
        )

    for service in ordered_services:
        category_key = (
            f"type:{service.type_service_id}"
            if service.type_service_id
            else f"legacy:{service.nom_service.strip().lower()}"
        )
        if category_key in seen_categories:
            continue
        seen_categories.add(category_key)
        service.nb_profils = profile_count_by_category.get(category_key, 1)
        categories.append(service)

    context = {
        "services": categories,
        "query": query,
        "lieu": lieu,
    }
    return render(request, "services/accueil.html", context)


def detail_service(request, service_id):
    service = get_object_or_404(
        Service.objects.select_related("prestataire", "prestataire__user", "type_service"),
        id=service_id,
        publier=True,
    )
    autres_profils = (
        Service.objects.filter(publier=True)
        .select_related("prestataire", "prestataire__user", "type_service")
        .exclude(id=service.id)
    )
    if service.type_service_id:
        autres_profils = autres_profils.filter(type_service_id=service.type_service_id)
    else:
        autres_profils = autres_profils.filter(nom_service=service.nom_service)

    avis_disponibles = Avis.objects.filter(service=service, visible=True)
    stats_avis = avis_disponibles.aggregate(note_moyenne=Avg("note"), nombre_avis=Count("id"))
    note_moyenne = stats_avis["note_moyenne"]
    nombre_avis = stats_avis["nombre_avis"] or 0

    if request.method == "POST":
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.service = service
            reservation.save()
            messages.success(
                request,
                "Votre demande a été envoyée. Le prestataire vous recontactera bientôt.",
            )
            return redirect("detail_service", service_id=service.id)
    else:
        form = ReservationForm()

    context = {
        "service": service,
        "form": form,
        "avis_disponibles": avis_disponibles[:6],
        "note_moyenne": note_moyenne,
        "nombre_avis": nombre_avis,
        "autres_profils": autres_profils[:6],
    }
    return render(request, "services/detail_service.html", context)


@staff_member_required(login_url="/admin/login/")
def dashboard_demandes(request):
    reservations_qs = Reservation.objects.select_related("service", "service__type_service").order_by("-id")
    service_options = (
        Service.objects.filter(reservation__isnull=False)
        .select_related("type_service")
        .distinct()
        .order_by("type_service__nom", "nom_service")
    )

    selected_service = request.GET.get("service", "").strip()
    selected_status = _canonical_status(request.GET.get("status", ""))

    filtered_reservations = reservations_qs
    if selected_service.isdigit():
        filtered_reservations = filtered_reservations.filter(service_id=int(selected_service))
    else:
        selected_service = ""

    if selected_status:
        filtered_reservations = filtered_reservations.filter(_status_filter_query(selected_status))

    status_counts = {
        status: reservations_qs.filter(_status_filter_query(status)).count() for status in STATUS_LABELS
    }

    dashboard_rows = []
    for reservation in filtered_reservations:
        row_status = _canonical_status(reservation.status) or "En attente"
        row_priority = _infer_priority(reservation)
        dashboard_rows.append(
            {
                "reservation": reservation,
                "status": row_status,
                "status_class": STATUS_CLASS_MAP.get(row_status, "status-waiting"),
                "priority": row_priority,
                "priority_class": PRIORITY_CLASS_MAP.get(row_priority, "priority-medium"),
            }
        )

    context = {
        "dashboard_rows": dashboard_rows,
        "service_options": service_options,
        "status_options": STATUS_LABELS,
        "selected_service": selected_service,
        "selected_status": selected_status,
        "stats": {
            "waiting": status_counts.get("En attente", 0),
            "in_progress": status_counts.get("En cours", 0),
            "done": status_counts.get("Terminee", 0),
            "cancelled": status_counts.get("Annulee", 0),
        },
    }
    return render(request, "services/dashboard_demandes.html", context)
