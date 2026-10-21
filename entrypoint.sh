#!/bin/sh
set -eu

# Apply the committed schema; do not generate new migration source at runtime.
python manage.py migrate --noinput

# Optional administrator bootstrap. Credentials come only from the environment.
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] || [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    : "${DJANGO_SUPERUSER_USERNAME:?Set both superuser username and password}"
    : "${DJANGO_SUPERUSER_PASSWORD:?Set both superuser username and password}"
    python - <<'PYTHON'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_concert.settings")
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
user = User.objects.filter(username=username).first()
if user is None:
    User.objects.create_superuser(
        username=username,
        email=os.environ.get("DJANGO_SUPERUSER_EMAIL", ""),
        password=os.environ["DJANGO_SUPERUSER_PASSWORD"],
    )
elif not (user.is_superuser and user.is_staff and user.is_active):
    raise RuntimeError("Configured administrator already exists without active admin privileges")
print("Administrator bootstrap ready")
PYTHON
fi

# The official Docker contract is port 8000; a platform may explicitly set PORT=8080.
if [ "$#" -eq 4 ] && [ "$1" = "python" ] && [ "$2" = "manage.py" ] && [ "$3" = "runserver" ]; then
    exec python manage.py runserver "0.0.0.0:${PORT:-8000}" --noreload
fi
exec "$@"
