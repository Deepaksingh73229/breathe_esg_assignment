#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.
This is the entry point for all Django management commands:
- python manage.py migrate      (run database migrations)
- python manage.py runserver    (start development server)
- python manage.py shell        (interactive Django shell)
- python manage.py seed_factors (custom command to load emission factors)
"""
import os
import sys


def main():
    """Run administrative tasks."""
    # Point Django to our settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
