# Back-end Development Capstone: Django application

Djirection's website for the IBM **Back-end Application Development Capstone Project**. This completes the official Django exercises: model fields and migrations, songs/lyrics, photos, registration and sessions, concert attendance, and concert administration.

Based on the [official template](https://github.com/ibm-developer-skills-network/sfvih-Back-end-Development-Capstone), commit `455089e3b5ccae97a1d8615671b63023c780c8c2`. Existing templates, static assets and empty `concert/tests.py` are unchanged. Runtime requirements and setup are limited to the packages this Django application uses; the Dockerfile, entrypoint and deployment manifest are completed for the deployment exercises. Code, added tests and documentation were prepared with OpenAI Codex assistance; see [AI_ACKNOWLEDGEMENT.md](AI_ACKNOWLEDGEMENT.md).

## Setup and run

Fresh local verification used **Python 3.10.11, Django 5.2.18, requests 2.32.5 and WhiteNoise 6.12.0**. Python **3.10 or newer** is required; the container uses Python 3.11. A matching local environment is:

```sh
python3.10 -m venv .venv
. .venv/bin/activate
python -m pip install --no-cache-dir -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py collectstatic --noinput
python manage.py test concert
python manage.py runserver 0.0.0.0:8000
```

Open `http://127.0.0.1:8000/`, or use the course lab's port-8000 application launcher. Check the running server from another terminal:

```sh
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/
```

Alternatively, run `sh bin/setup.sh` with a Python 3.10+ interpreter installed; `PYTHON_BIN=python3.11 sh bin/setup.sh` selects a specific interpreter. The script creates `.venv`, installs the pinned requirements and applies migrations. It does not provision an unused Postgres container or change shell startup files. A separate compatibility check passed with existing Django 4.2.2 on Python 3.10.11; the pinned deployment dependency is Django 5.2.18.

## Required application flows

- `/` displays the original home page and navigation.
- `/song/` displays the exact single sample song required by Part 3; its title targets the existing Bootstrap lyrics modal.
- `/photos/` displays the exact single sample event photo required by Part 3.
- `/signup/` validates registration, hashes passwords, automatically logs in new users, and rejects duplicate usernames without changing existing accounts.
- `/login/` authenticates through Django; `/logout/` clears the session and returns to login. Password whitespace is preserved consistently. The supplied GET logout link is retained.
- `/concert/` and `/concert-detail/<id>` require login and display the current user's RSVP state.
- `/concert_attendee/` accepts authenticated, CSRF-protected POST requests and creates or updates only the current user's record. Invalid choices are rejected and missing concerts return 404.
- `/admin/` includes the registered Concert model. Run `python manage.py createsuperuser`, choose credentials privately, then add a concert with name, duration, city and date.

`Photo` and `Song` retain the template's `managed = False` behavior: their fields describe external resources. Migrations create Concert/ConcertAttending and Django's authentication, admin and session tables. The exact one-song/one-photo samples are intentional for Part 3, before connecting the services in the deployment exercise.

## Configuration for deployment

| Variable | Meaning |
|---|---|
| `SONGS_SERVICE_URL` | Base URL; Django requests `/song` and reads the `songs` collection |
| `PICTURES_SERVICE_URL` | Base URL; Django requests `/picture` and reads its JSON array |
| `DJANGO_DB_PATH` | SQLite path; defaults to ignored `db.sqlite3` |
| `DJANGO_DEBUG` | Defaults to `1` for the lab; set `0` for a configured deployed environment |
| `DJANGO_SECRET_KEY` | Required when debug is disabled; supply through the environment |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated accepted host names |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated full trusted origins including `https://` |

Service values are base URLs without `/song` or `/picture`. Empty URLs use the required Part 3 samples. A configured backend failure returns 503 instead of silently substituting sample data; network requests have a five-second timeout. Default hosts/CSRF settings include the course lab domains. Persistent hosted accounts and attendance require durable storage at the configured database path.

## Verified locally — 22 October 2026

All migrations applied to a task-specific SQLite database. Django's system check passed and `makemigrations --check --dry-run` found no drift. **21 added application tests passed**, covering pages/sample content, modal markup, signup/password/session behavior, duplicate/invalid input, login/logout, isolated RSVP updates, CSRF, admin creation/access, and configured service contracts/failures. The starter's empty test file is preserved. The suite also passed with existing Django 4.2.2 as a compatibility check.

A real running HTTP server passed home/song/photo/static-asset requests, CSRF rejection, signup and later login with an exact whitespace-containing password, attendance changes, logout, admin login and concert creation through the actual admin form. Temporary test accounts and concerts were cleaned up. No real user database was used. The entrypoint separately passed fresh-schema migration, startup without a default account, repeated optional administrator bootstrap with a hashed password and one account, and real HTTP startup using an overridden `PORT`.

Browser screenshots, a visible modal click, cloud deployment and integration with the actual deployed Pictures/Songs services remain separate checks. Local results do not establish a Coursera grade.

## Container and cluster deployment

The Dockerfile uses `python:3.11-slim` for compatibility with pinned Django 5.2.18, retaining the official lab's port **8000** and `python manage.py runserver 0.0.0.0:8000` command. It installs the application's pinned Django/requests/WhiteNoise dependencies and copies its source. During image build, `collectstatic --noinput` collects and compresses static assets into `/app/staticfiles`; the build then makes that tree readable and non-writable. The runtime entrypoint does not collect or write static files, so an arbitrary OpenShift UID needs only read access to the application tree. The entrypoint applies committed migrations first. It starts without an auto-created administrator unless both `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD` are provided through the environment; `DJANGO_SUPERUSER_EMAIL` is optional. Bootstrap is idempotent and never replaces an existing password or promotes a normal account. No administrator credentials are included in source.

```sh
docker build -t djangoserver:1 .
docker run --rm -p 8000:8000 djangoserver:1
```

`PORT=8080` can override the runtime bind port when a hosting platform requires it; match the platform's configured container port. The official Docker/manifest default remains 8000. An S2I builder that bypasses the Dockerfile must invoke `entrypoint.sh` before serving and use the same configured bind port.

Before applying `deployment.yml`, replace `REPLACE_NAMESPACE` in its image reference with the actual registry namespace and push that image. Create a `djangoserver-config` ConfigMap containing real service base URLs and host/CSRF settings, and a `djangoserver-secret` Secret containing `DJANGO_SECRET_KEY` and any optional administrator bootstrap fields. Keep their values outside Git. The manifest references those objects and exposes port 8000; no sample URLs are presented as deployed services.

```sh
kubectl apply -f deployment.yml
kubectl rollout status deployment/djangoserver
kubectl port-forward service/djangoserver 8000:8000
```

The lab's runserver command is retained for course evidence. WhiteNoise now serves the collected CSS, JavaScript, fonts and admin assets with `DJANGO_DEBUG=0`; HTTPS and configured secrets are still required for deployment. Its middleware follows Django's SecurityMiddleware and the compressed storage preserves the supplied asset URLs. The setup follows the [primary WhiteNoise Django guide](https://whitenoise.readthedocs.io/en/stable/django.html) and pins [WhiteNoise 6.12.0](https://pypi.org/project/whitenoise/6.12.0/). The container's default SQLite database is in `/tmp` for random-UID compatibility and is ephemeral; use durable storage when persistence is required. Image build, registry push, cluster apply, real service URLs and browser deployment screenshots must be verified in the actual cloud environment.

A separate static-file regression check ran the actual entrypoint with `DJANGO_DEBUG=0`, an ephemeral secret and database, and a read-only collected tree. All seven referenced/check assets returned HTTP 200, including application CSS, Bootstrap CSS/JS and admin CSS. Bootstrap gzip decompressed to the original bytes; the collected file hashes remained unchanged. The 21 existing application tests, system and migration-drift checks also passed after this change. This verifies source behavior locally; the new image still needs a real cloud build.
