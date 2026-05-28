"""
Base model abstractions for the entire Breathe ESG platform.

Design Principles:
1. UUID Primary Keys  — prevent enumeration attacks, safe in distributed systems.
2. Timestamped        — every record knows when it was created / last modified.
3. User Trackable     — every record knows WHO created / last modified it.
4. Soft Deletable     — records are never physically deleted (preserves audit trails).
5. Tenant Scoped      — all business data belongs to an Organization.
"""
import uuid
from django.db import models
from django.conf import settings   # Always use settings.AUTH_USER_MODEL to avoid circular imports


class UUIDPrimaryKeyMixin(models.Model):
    """Replaces auto-incrementing ID with UUID4 for security and portability."""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID4 primary key. Never sequential, never guessable.",
    )

    class Meta:
        abstract = True


class TimestampedMixin(models.Model):
    """Adds created_at / updated_at. Critical for emission factor vintage tracking."""
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Immutable creation timestamp.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp.",
    )

    class Meta:
        abstract = True


class UserTrackableMixin(models.Model):
    """Tracks which user created / last modified each record. Required for audit defense."""
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        help_text="User who created this record.",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        help_text="User who last modified this record.",
    )

    class Meta:
        abstract = True


class SoftDeletableMixin(models.Model):
    """
    Soft deletion — carbon data is NEVER physically deleted.

    Rationale: A record may have been included in a submitted GHG report.
    Deleting it would break the audit trail. Instead we mark it deleted and
    exclude it from active queries.
    """
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft-deletion flag. True = logically deleted, physically preserved.",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_deleted",
    )

    class Meta:
        abstract = True


class BaseManager(models.Manager):
    """Default manager that automatically excludes soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(
    UUIDPrimaryKeyMixin,
    TimestampedMixin,
    UserTrackableMixin,
    SoftDeletableMixin,
    models.Model,
):
    """
    Universal base model: UUID PK + timestamps + user tracking + soft deletion.

    Two managers:
    - objects       → excludes deleted records (use for all normal queries)
    - all_objects   → includes deleted records (use for audit queries only)
    """
    objects = BaseManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class TenantModel(BaseModel):
    """
    Base model for all data belonging to a specific client organization.

    Multi-tenancy strategy: Single Database, Shared Schema, application-level isolation.
    Every query against a TenantModel MUST include an organization_id filter.
    The DB index on organization ensures this remains performant at scale.
    """
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
        help_text="The client organization that owns this record.",
    )

    class Meta:
        abstract = True