"""
Django settings for running bakerydemo in WebAssembly via Pyodide.

Inherits from base settings, then overrides everything that relies on
external services (Postgres, Redis, Elasticsearch, email, CSP, etc.)
so the app can run entirely inside a browser service worker with SQLite.
"""

import os

from .base import *  # noqa: F403, F401

# Fix the template directory to use an absolute path based on this file's
# location (the base settings' PROJECT_DIR may resolve via os.path.abspath
# relative to the wrong cwd inside Pyodide's virtual filesystem).
_WASM_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES[0]["DIRS"] = [  # noqa: F405
    os.path.join(_WASM_PROJECT_DIR, "templates"),
]

# Also fix the static files and media dirs to use the absolute path.
STATICFILES_DIRS = [  # noqa: F405
    os.path.join(_WASM_PROJECT_DIR, "static"),
]
STATIC_ROOT = os.path.join(_WASM_PROJECT_DIR, "collect_static")
MEDIA_ROOT = os.path.join(_WASM_PROJECT_DIR, "media")
PROJECT_DIR = _WASM_PROJECT_DIR  # noqa: F811

DEBUG = True

SECRET_KEY = "wasm-playground-not-secret"  # noqa: S105

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
]

# SQLite on Emscripten's IDBFS-backed virtual filesystem (persists to IndexedDB)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/home/pyodide/wagtail_db/db.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

WAGTAILADMIN_BASE_URL = "http://localhost:8000"

# Use plain FileSystemStorage for static files (no manifest hashing needed
# inside the WASM environment -- StaticFilesHandler serves them directly).
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Database search backend (already the default in base, but be explicit)
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    },
}

# AVIF quality setting (the init.py registers a JPEG-based AVIF stub if the
# real encoder isn't available in the WASM Pillow build)
WAGTAILIMAGES_AVIF_QUALITY = 60

ADMIN_PASSWORD = "changeme"

# Disable password validators for the playground (speeds up user creation)
AUTH_PASSWORD_VALIDATORS = []

# Use a fast password hasher suitable for a demo (the pure-Python pbkdf2_hmac
# fallback in init.py is too slow at Django's default 870k iterations).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
