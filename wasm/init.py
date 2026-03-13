"""
Bootstrap script that runs inside Pyodide in the service worker.

Sets up Django, runs migrations, loads fixture data and media files,
creates a superuser, and exposes a WebTest TestApp for handling requests.
"""

import os
import shutil

# Pyodide/Emscripten doesn't support threading. Monkey-patch
# concurrent.futures so Wagtail's image rendition generation (which uses
# ThreadPoolExecutor to create multiple renditions in parallel) runs
# synchronously instead of crashing.
import concurrent.futures
import concurrent.futures.thread


class _SyncExecutor(concurrent.futures.Executor):
    def __init__(self, *args, **kwargs):
        pass

    def submit(self, fn, /, *args, **kwargs):
        fut = concurrent.futures.Future()
        try:
            fut.set_result(fn(*args, **kwargs))
        except Exception as exc:
            fut.set_exception(exc)
        return fut


concurrent.futures.ThreadPoolExecutor = _SyncExecutor
concurrent.futures.thread.ThreadPoolExecutor = _SyncExecutor

# Pillow in WASM may lack the AVIF encoder. If so, register a stub that
# saves as JPEG instead -- this prevents Wagtail's {% picture %} tag
# (which requests format-{avif,webp,jpeg}) from crashing.
from PIL import Image

if "AVIF" not in Image.SAVE:
    def _avif_save_stub(im, fp, filename=None, **kwargs):
        if im.mode in ("RGBA", "LA", "PA"):
            im = im.convert("RGB")
        jpeg_kwargs = {}
        if "quality" in kwargs and isinstance(kwargs["quality"], int):
            jpeg_kwargs["quality"] = kwargs["quality"]
        return Image.SAVE["JPEG"](im, fp, filename, **jpeg_kwargs)

    Image.register_save("AVIF", _avif_save_stub)
    Image.register_extension("AVIF", ".avif")
    Image.register_mime("AVIF", "image/avif")

# Pyodide's hashlib may lack pbkdf2_hmac (used by Django's password hashing).
# Provide a pure-Python fallback.
import hashlib
import hmac as _hmac_mod
import struct

if not hasattr(hashlib, "pbkdf2_hmac"):
    def _pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
        if isinstance(password, str):
            password = password.encode("utf-8")
        if isinstance(salt, str):
            salt = salt.encode("utf-8")
        mac = _hmac_mod.new(password, digestmod=hash_name)
        dk_len = dklen or mac.digest_size
        blocks = (dk_len + mac.digest_size - 1) // mac.digest_size
        dk = b""
        for block_num in range(1, blocks + 1):
            u = _hmac_mod.new(
                password, salt + struct.pack(">I", block_num), hash_name
            ).digest()
            result = u
            for _ in range(iterations - 1):
                u = _hmac_mod.new(password, u, hash_name).digest()
                result = bytes(a ^ b for a, b in zip(result, u))
            dk += result
        return dk[:dk_len]

    hashlib.pbkdf2_hmac = _pbkdf2_hmac

import django

os.environ["DJANGO_SETTINGS_MODULE"] = "bakerydemo.settings.wasm"
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

django.setup()

from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.core.management.commands.migrate import Command as MigrateCommand  # noqa: E402

# _wasm_db_exists is set by the service worker before running this script.
# If True, the database was loaded from IndexedDB and we can skip fixture loading.
try:
    _skip_fixtures = _wasm_db_exists  # noqa: F821 - injected by worker.js
except NameError:
    _skip_fixtures = False

print("[wasm] Running migrations...")
MigrateCommand().handle(
    database="default",
    skip_checks=False,
    verbosity=0,
    interactive=False,
    app_label=None,
    migration_name=None,
    noinput=True,
    fake=False,
    fake_initial=False,
    plan=False,
    run_syncdb=False,
    check=False,
    prune=False,
    check_unapplied=False,
)
print("[wasm] Migrations complete.")

if _skip_fixtures:
    print("[wasm] Database loaded from IndexedDB -- skipping fixture loading.")
else:
    # Copy fixture media files into MEDIA_ROOT on the virtual filesystem.
    fixtures_dir = os.path.join(settings.PROJECT_DIR, "base", "fixtures")
    fixtures_media = os.path.join(fixtures_dir, "media")

    if os.path.isdir(fixtures_media):
        print("[wasm] Copying fixture media files...")
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        for dirpath, dirnames, filenames in os.walk(fixtures_media):
            rel = os.path.relpath(dirpath, fixtures_media)
            dest_dir = os.path.join(settings.MEDIA_ROOT, rel)
            os.makedirs(dest_dir, exist_ok=True)
            for fname in filenames:
                src = os.path.join(dirpath, fname)
                dst = os.path.join(dest_dir, fname)
                shutil.copy2(src, dst)
        print("[wasm] Media files copied.")

    # Load the fixture data.
    fixture_file = os.path.join(fixtures_dir, "bakerydemo.json")

    from wagtail.models import Page, Site  # noqa: E402

    if Site.objects.filter(hostname="localhost").exists():
        Site.objects.get(hostname="localhost").delete()
    if Page.objects.filter(title="Welcome to your new Wagtail site!").exists():
        Page.objects.get(title="Welcome to your new Wagtail site!").delete()

    print("[wasm] Loading fixture data...")
    call_command("loaddata", fixture_file, verbosity=0)
    print("[wasm] Fixture data loaded.")

    print("[wasm] Building search index...")
    call_command("update_index", verbosity=0)
    print("[wasm] Search index built.")

    # Ensure the admin user has a password hashed with the active hasher.
    from django.contrib.auth.models import User  # noqa: E402

    try:
        user = User.objects.get(username="admin")
    except User.DoesNotExist:
        user = User(username="admin", is_staff=True, is_superuser=True)

    user.set_password(settings.ADMIN_PASSWORD)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("[wasm] Admin password reset (password: changeme).")

# Set up the WSGI app wrapped in StaticFilesHandler + WebTest TestApp.
from django.contrib.staticfiles.handlers import StaticFilesHandler  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402
from webtest import TestApp  # noqa: E402

wsgi_application = StaticFilesHandler(get_wsgi_application())
app = TestApp(wsgi_application)

print("[wasm] Wagtail is ready!")
