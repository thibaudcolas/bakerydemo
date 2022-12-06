import dj_database_url

from .base import *  # noqa: F403, F401

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# WAGTAILADMIN_BASE_URL required for notification emails
WAGTAILADMIN_BASE_URL = "http://localhost:8000"

ALLOWED_HOSTS = ["*"]

db_from_env = dj_database_url.config(conn_max_age=500)
DATABASES["default"].update(db_from_env)
