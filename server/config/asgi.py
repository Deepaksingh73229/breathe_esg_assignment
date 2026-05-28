"""
ASGI config for Breathe ESG.

ASGI = Asynchronous Server Gateway Interface. Required for WebSockets or
async views. Included for future-proofing but not actively used in v1.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_asgi_application()
