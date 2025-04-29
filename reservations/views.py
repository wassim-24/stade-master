from datetime import datetime, date, time, timedelta
import random
from django.contrib.auth import login as auth_login
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q
from .decorators import only_owner, owner_required, player_required
from .forms import (
    LoginForm,
    SignUpForm,
    StadeForm,
    StadeImageFormSet,
    ProfileForm,
)
from .models import Stade, Booking, User


# ─── Utilitaires ───────────────────────────────────────────────────────────────

def redirect_by_role(user):
    """Envoie l’utilisateur sur le bon tableau de bord."""
    return redirect("home_owner" if user.is_owner else "home_player")


def slot_is_past(the_day: date, the_time: time) -> bool:
    """Vérifie si un créneau est déjà dans le passé."""
    now = datetime.now()
    if the_day < now.date():
        return True
    if the_day > now.date():
        return False
    return the_time <= now.time().replace(microsecond=0)


# ─── Authentification ─────────────────────────────────────────────────────────

def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        # authentifie et logue directement l'utilisateur
        auth_login(request, user,
                   backend="reservations.backends.PhoneOrUsernameBackend")
        # redirige vers owner _ou_ player suivant is_owner
        return redirect_by_role(user)

    return render(request, "reservations/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        # support login via phone
        try:
            username = User.objects.get(phone=username).username
        except User.DoesNotExist:
            pass

        user = authenticate(
            request,
            username=username,
            password=password,
            backend="reservations.backends.PhoneOrUsernameBackend",
        )
        if user:
            login(request, user)
            return redirect_by_role(user)
        form.add_error(None, "Identifiants invalides")

    return render(request, "reservations/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


# ─── Tableaux de bord ─────────────────────────────────────────────────────────

@login_required
@owner_required
def owner_home(request):
    return render(request, "reservations/home_owner.html")


@login_required
@player_required
def player_home(request):
    stades_qs = (
        Stade.objects.filter(est_ouvert=True)
        .prefetch_related("images")
        .order_by("nom")
    )
    paginator = Paginator(stades_qs, 12)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    stades = []
    for stade in page_obj.object_list:
        photos = list(stade.images.all())
        cover = random.choice(photos).image.url if photos else None
        stades.append((stade, cover))

    return render(request, "reservations/home_player.html", {
        "stades": stades,
        "page_obj": page_obj,
    })


# ─── Gestion propriétaire ─────────────────────────────────────────────────────

@login_required
@only_owner
def owner_manage(request):
    try:
        stade = request.user.stade
    except Stade.DoesNotExist:
        stade = None

    # Création
    if stade is None:
        form = StadeForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            stade = form.save(commit=False)
            stade.owner = request.user
            stade.save()
            messages.success(request, "Stade ajouté ! Ajoutez vos photos.")
            return redirect("owner_manage")
        return render(request, "reservations/owner_manage_create.html", {"form": form})

    # Édition + photos
    form = StadeForm(request.POST or None, instance=stade)
    formset = StadeImageFormSet(
        request.POST or None, request.FILES or None, instance=stade
    )
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, "Modifications enregistrées.")
        return redirect("owner_manage")

    return render(request, "reservations/owner_manage_edit.html", {
        "form": form,
        "formset": formset,
        "stade": stade,
    })


# ─── Fiche stade + réservation ────────────────────────────────────────────────

@login_required
@player_required
def stade_detail(request, pk):
    stade = get_object_or_404(
        Stade.objects.prefetch_related("images"),
        pk=pk,
        est_ouvert=True
    )
    try:
        selected_day = date.fromisoformat(request.GET.get("day", ""))
    except ValueError:
        selected_day = date.today()

    days = [selected_day + timedelta(days=i) for i in range(7)]
    raw_hours = [
        time(0, 0), time(1, 30), time(3, 0), time(4, 30),
        time(6, 0), time(7, 30), time(9, 0), time(10, 30),
        time(12, 0), time(13, 30), time(15, 0), time(16, 30),
        time(18, 0), time(19, 30), time(21, 0), time(22, 30),
    ]
    booked_hours = set(
        Booking.objects.filter(
            stade=stade, jour=selected_day
        ).values_list("heure", flat=True)
    )

    slots = [
        {
            "label": h.strftime("%H:%M"),
            "time": h,
            "is_past": slot_is_past(selected_day, h),
            "is_booked": h in booked_hours,
        }
        for h in raw_hours
    ]
    return render(request, "reservations/stade_detail.html", {
        "stade": stade,
        "cover": stade.images.first(),
        "days": days,
        "selected_day": selected_day,
        "slots": slots,
    })


@require_POST
@login_required
@player_required
def reserver_slot(request, pk):
    stade = get_object_or_404(Stade, pk=pk, est_ouvert=True)
    date_str = request.POST.get("date")
    time_str = request.POST.get("time")

    try:
        the_day = date.fromisoformat(date_str)
        the_time = datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return JsonResponse({"ok": False, "error": "Créneau invalide."})

    # ✅ Vérifier si l'utilisateur a déjà une réservation ce jour-là pour ce stade
    existing_booking = Booking.objects.filter(
        user=request.user,
        stade=stade,
        jour=the_day
    ).exists()

    if existing_booking:
        return JsonResponse({"ok": False, "error": "Vous avez déjà réservé pour ce jour sur ce stade."})

    # 🔥 Vérifier si le créneau est déjà passé
    if slot_is_past(the_day, the_time):
        return JsonResponse({"ok": False, "error": "Créneau déjà passé."})

    # 🔥 Vérifier si le créneau est déjà réservé par quelqu'un d'autre
    if Booking.objects.filter(stade=stade, jour=the_day, heure=the_time).exists():
        return JsonResponse({"ok": False, "error": "Créneau déjà réservé."})

    # 🔥 Si tout est bon : créer la réservation
    Booking.objects.create(
        stade=stade,
        user=request.user,
        jour=the_day,
        heure=the_time
    )
    return JsonResponse({"ok": True})



# ─── Mes réservations (player) ───────────────────────────────────────────────

@login_required
@player_required
def player_bookings(request):
    bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related("stade")
        .prefetch_related("stade__images")
        .order_by("-jour", "-heure")
    )
    # Ajout d’un attribut .cover pour le template
    for b in bookings:
        b.cover = b.stade.images.first()
    return render(request, "reservations/player_bookings.html", {
        "bookings": bookings,
    })


# ─── Profil (player & owner) ─────────────────────────────────────────────────

def _profile(request):
    """Logique partagée pour player_profile et owner_profile."""
    if request.method == "POST":
        if "profile_submit" in request.POST:
            pform = ProfileForm(request.POST, instance=request.user)
            if pform.is_valid():
                pform.save()
                messages.success(request, "Profil mis à jour.")
                return redirect(request.path)
        elif "password_submit" in request.POST:
            pw_form = PasswordChangeForm(request.user, request.POST)
            if pw_form.is_valid():
                user = pw_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Mot de passe changé.")
                return redirect(request.path)
    else:
        pform = ProfileForm(instance=request.user)
        pw_form = PasswordChangeForm(request.user)

    return render(request, "reservations/profile.html", {
        "pform": pform,
        "pw_form": pw_form,
    })


@login_required
@player_required
def player_profile(request):
    return _profile(request)


@login_required
@owner_required
def owner_profile(request):
    return _profile(request)


def dummy(request):
    return HttpResponse("<h1>En construction…</h1>")




@login_required
@owner_required
def owner_bookings(request):
    # Récupère le stade du propriétaire (ou 404 si aucun)
    stade = get_object_or_404(Stade, owner=request.user)
    # Toutes les réservations pour ce stade, avec l'utilisateur lié
    bookings = (
        Booking.objects
        .filter(stade=stade)
        .select_related('user')
        .order_by('jour', 'heure')
    )
    return render(request, "reservations/owner_bookings.html", {
        "stade":   stade,
        "bookings": bookings,
    })





@login_required
@player_required
def player_search(request):
    q = request.GET.get('q', '').strip()
    # only open stadia
    stades_qs = Stade.objects.filter(est_ouvert=True)
    if q:
        stades_qs = stades_qs.filter(
            Q(nom__icontains=q)     # recherche dans le nom
            | Q(adresse__icontains=q)  # **et** dans l’adresse
        )
    stades_qs = stades_qs.prefetch_related('images').order_by('nom')

    paginator = Paginator(stades_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    stades = []
    for stade in page_obj.object_list:
        photos = list(stade.images.all())
        cover = random.choice(photos).image.url if photos else None
        stades.append((stade, cover))

    return render(request, "reservations/player_search.html", {
        "stades":   stades,
        "page_obj": page_obj,
        "q":        q,
    })