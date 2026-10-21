"""Added application-contract tests; the original empty tests.py is preserved."""

from datetime import date
from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from concert.models import Concert, ConcertAttending


class ApplicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("listener", password="Test-only-password-42")
        cls.other = User.objects.create_user("other", password="Other-test-password-42")
        cls.admin = User.objects.create_superuser(
            "testadmin", "testadmin@example.invalid", "Admin-test-password-42"
        )
        cls.concert = Concert.objects.create(
            concert_name="Djirection live", duration=2, city="London", date=date(2030, 7, 1)
        )

    def test_home_and_public_auth_forms(self):
        for name in ("index", "signup", "login"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_exact_single_sample_song_and_modal_markup(self):
        response = self.client.get(reverse("songs"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["songs"]), 1)
        self.assertContains(response, "duis faucibus accumsan odio curabitur convallis")
        self.assertContains(response, 'data-bs-target="#abc1"')
        self.assertContains(response, "Morbi non lectus.")
        self.assertContains(response, "bootstrap.bundle.min.js")

    def test_exact_single_sample_photo(self):
        response = self.client.get(reverse("photos"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["photos"]), 1)
        self.assertContains(response, "http://dummyimage.com/136x100.png/5fa2dd/ffffff")
        self.assertContains(response, "Washington, District of Columbia")

    def test_signup_hashes_password_and_logs_new_user_in(self):
        response = self.client.post(reverse("signup"), {
            "username": "newlistener", "password": "New-test-password-42"
        })
        self.assertRedirects(response, reverse("index"))
        user = User.objects.get(username="newlistener")
        self.assertNotEqual(user.password, "New-test-password-42")
        self.assertTrue(user.check_password("New-test-password-42"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_signup_keeps_existing_account(self):
        response = self.client.post(reverse("signup"), {
            "username": "listener", "password": "Replacement-test-password-42"
        })
        self.assertContains(response, "user already exists")
        self.assertEqual(User.objects.filter(username="listener").count(), 1)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Test-only-password-42"))

    def test_invalid_signup_does_not_create_an_account(self):
        initial = User.objects.count()
        for payload in ({}, {"username": "bad name", "password": "Valid-test-password"},
                        {"username": "validname", "password": "ab"}):
            with self.subTest(payload=payload):
                response = self.client.post(reverse("signup"), payload)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.assertEqual(User.objects.count(), initial)

    def test_login_rejects_invalid_password(self):
        response = self.client.post(reverse("login"), {
            "username": "listener", "password": "Wrong-test-password"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_then_logout(self):
        response = self.client.post(reverse("login"), {
            "username": "listener", "password": "Test-only-password-42"
        })
        self.assertRedirects(response, reverse("index"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertRedirects(self.client.get(reverse("logout")), reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_signup_and_login_preserve_whitespace_in_password(self):
        password = "  Whitespace-test-password-42  "
        self.client.post(reverse("signup"), {
            "username": "spacelistener", "password": password
        })
        self.client.get(reverse("logout"))
        response = self.client.post(reverse("login"), {
            "username": "spacelistener", "password": password
        })
        self.assertRedirects(response, reverse("index"))
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            User.objects.get(username="spacelistener").pk,
        )

    def test_concert_pages_require_authentication(self):
        for url in (reverse("concerts"), reverse("concert_detail", args=[self.concert.pk])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse("login")))

    def test_concert_list_and_detail_use_current_users_status(self):
        ConcertAttending.objects.create(
            concert=self.concert, user=self.other, attending="Attending"
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("concerts"))
        self.assertEqual(response.context["concerts"][0]["status"], "-")
        self.assertContains(response, "Djirection live")
        response = self.client.get(reverse("concert_detail", args=[self.concert.pk]))
        self.assertEqual(response.context["status"], "-")
        self.assertContains(response, "London")
        self.assertEqual(self.client.get(reverse("concert_detail", args=[999999])).status_code, 404)

    def test_attendance_creates_then_updates_only_current_user(self):
        self.client.force_login(self.user)
        for status in ("Attending", "Not Attending", "-"):
            response = self.client.post(reverse("concert_attendee"), {
                "concert_id": self.concert.pk, "attendee_choice": status,
                "user": self.other.pk,
            })
            self.assertRedirects(response, reverse("concerts"))
            record = ConcertAttending.objects.get(concert=self.concert, user=self.user)
            self.assertEqual(record.attending, status)
            self.assertEqual(ConcertAttending.objects.filter(concert=self.concert).count(), 1)
            self.assertFalse(ConcertAttending.objects.filter(user=self.other).exists())

    def test_attendance_rejects_invalid_or_missing_concert_and_choice(self):
        self.client.force_login(self.user)
        for payload, code in (({}, 400), ({"concert_id": "invalid"}, 400),
                              ({"concert_id": 999999, "attendee_choice": "Attending"}, 404),
                              ({"concert_id": self.concert.pk, "attendee_choice": "invalid"}, 400)):
            self.assertEqual(self.client.post(reverse("concert_attendee"), payload).status_code, code)
        self.assertFalse(ConcertAttending.objects.exists())
        self.assertEqual(self.client.get(reverse("concert_attendee")).status_code, 405)

    def test_anonymous_attendance_cannot_write(self):
        response = self.client.post(reverse("concert_attendee"), {
            "concert_id": self.concert.pk, "attendee_choice": "Attending"
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ConcertAttending.objects.exists())

    def test_csrf_required_for_attendance(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(reverse("concert_attendee"), {
            "concert_id": self.concert.pk, "attendee_choice": "Attending"
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ConcertAttending.objects.exists())

    def test_admin_can_create_concert_with_complete_model_fields(self):
        self.client.force_login(self.admin)
        url = reverse("admin:concert_concert_add")
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, {
            "concert_name": "New concert", "duration": 3, "city": "Paris",
            "date": "2030-08-01", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        concert = Concert.objects.get(concert_name="New concert")
        self.assertEqual(concert.date, date(2030, 8, 1))
        self.assertEqual(concert.duration, 3)

    def test_normal_user_cannot_access_concert_admin(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin:concert_concert_add"))
        self.assertEqual(response.status_code, 302)


class ConfiguredServicesTests(TestCase):
    @override_settings(SONGS_SERVICE_URL="https://songs.example.invalid")
    @patch("concert.services.requests.get")
    def test_song_service_collection_used_when_configured(self, get):
        get.return_value = Mock()
        get.return_value.json.return_value = {
            "songs": [{"id": 77, "title": "Service song", "lyrics": "Service lyrics"}]
        }
        response = self.client.get(reverse("songs"))
        self.assertContains(response, "Service song")
        self.assertEqual(response.context["songs"][0]["id"], 77)
        get.assert_called_once_with("https://songs.example.invalid/song", timeout=5)

    @override_settings(PICTURES_SERVICE_URL="https://pictures.example.invalid/")
    @patch("concert.services.requests.get")
    def test_pictures_service_collection_used_when_configured(self, get):
        get.return_value = Mock()
        get.return_value.json.return_value = [{
            "id": 88, "pic_url": "https://example.invalid/image.png",
            "event_country": "Country", "event_state": "State", "event_city": "City",
            "event_date": "2030-01-01",
        }]
        response = self.client.get(reverse("photos"))
        self.assertContains(response, "https://example.invalid/image.png")
        get.assert_called_once_with("https://pictures.example.invalid/picture", timeout=5)

    @override_settings(SONGS_SERVICE_URL="https://songs.example.invalid")
    @patch("concert.services.requests.get", side_effect=requests.ConnectionError)
    def test_configured_failure_does_not_silently_return_sample_data(self, get):
        response = self.client.get(reverse("songs"))
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "duis faucibus", status_code=503)

    @override_settings(SONGS_SERVICE_URL="https://songs.example.invalid")
    @patch("concert.services.requests.get")
    def test_invalid_service_schema_returns_503(self, get):
        get.return_value = Mock()
        get.return_value.json.return_value = {"songs": "unexpected"}
        self.assertEqual(self.client.get(reverse("songs")).status_code, 503)
