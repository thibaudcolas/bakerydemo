from bakerydemo.settings.dev import *  # noqa

# Make sure the site can be accessed from any host, e.g. for cross-browser testing.
ALLOWED_HOSTS = "*"

# Disable most validators to allow the user of simpler passwords.
# We still want at least one validator to be configured to test password validation.
AUTH_PASSWORD_VALIDATORS = [
    # {
    #     'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    # },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}
]

# The Wagtail styleguide is a valuable UI testing view.
INSTALLED_APPS = INSTALLED_APPS + ["wagtail.contrib.styleguide"]

# We want browser automation to be able to read the session cookie’s value.
SESSION_COOKIE_HTTPONLY = False
