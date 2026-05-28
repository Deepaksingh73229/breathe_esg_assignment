"""
Audit app configuration.

The Audit app provides immutable logging of all significant actions.
Every mutation to business data creates an AuditLog entry.

This is not just "good practice" - it's a regulatory requirement.
Auditors will ask: "Who changed this, when, and why?"
Our answer must be: "AuditLog row #12345, performed by user@company.com at 2024-03-15 14:32:07"
"""
from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit Trail"
