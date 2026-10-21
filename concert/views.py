"""Course application flows completed with OpenAI Codex assistance."""

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from concert.forms import LoginForm, SignUpForm
from concert.models import Concert, ConcertAttending
from concert.services import ServiceUnavailable, load_photos, load_songs


@require_http_methods(["GET", "POST"])
def signup(request):
    form = SignUpForm(request.POST if request.method == "POST" else None)
    message = None
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            message = "user already exists"
        else:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username, password=form.cleaned_data["password"]
                    )
            except IntegrityError:
                message = "user already exists"
            else:
                login(request, user)
                return redirect("index")
    return render(request, "signup.html", {"form": form, "message": message})


def index(request):
    return render(request, "index.html")


def songs(request):
    try:
        song_list = load_songs()
    except ServiceUnavailable:
        return HttpResponse("Songs are temporarily unavailable.", status=503)
    return render(request, "songs.html", {"songs": song_list})


def photos(request):
    try:
        photo_list = load_photos()
    except ServiceUnavailable:
        return HttpResponse("Photos are temporarily unavailable.", status=503)
    return render(request, "photos.html", {"photos": photo_list})


@require_http_methods(["GET", "POST"])
def login_view(request):
    form = LoginForm(
        request=request, data=request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("index")
    return render(request, "login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    # The supplied navigation uses a GET link; retain that course UI contract.
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def concerts(request):
    statuses = dict(ConcertAttending.objects.filter(user=request.user).values_list(
        "concert_id", "attending"
    ))
    concert_list = [
        {"concert": concert, "status": statuses.get(concert.pk, "-")}
        for concert in Concert.objects.order_by("date", "pk")
    ]
    return render(request, "concerts.html", {"concerts": concert_list})


@login_required(login_url="login")
def concert_detail(request, id):
    concert = get_object_or_404(Concert, pk=id)
    attendance = concert.attendee.filter(user=request.user).first()
    status = attendance.attending if attendance else "-"
    return render(request, "concert_detail.html", {
        "concert_details": concert,
        "status": status,
        "attending_choices": ConcertAttending.AttendingChoices.choices,
    })


@login_required(login_url="login")
@require_POST
def concert_attendee(request):
    try:
        concert_id = int(request.POST.get("concert_id", ""))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("A valid concert is required.")
    concert = get_object_or_404(Concert, pk=concert_id)
    status = request.POST.get("attendee_choice")
    if status not in ConcertAttending.AttendingChoices.values:
        return HttpResponseBadRequest("Choose a valid attendance status.")
    ConcertAttending.objects.update_or_create(
        concert=concert, user=request.user, defaults={"attending": status}
    )
    return redirect("concerts")
