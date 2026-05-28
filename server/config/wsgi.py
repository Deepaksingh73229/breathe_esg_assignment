"""
WSGI config for Breathe ESG.

WSGI = Web Server Gateway Interface. This is the entry point that production
servers like Gunicorn use to communicate with our Django application.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
