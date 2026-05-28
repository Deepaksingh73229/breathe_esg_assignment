"""
Organization and membership models.

An Organization represents a single client company (e.g., "Acme Corp").
All emissions data, facilities, and audit trails are scoped to an Organization.

User-Organization relationship is many-to-many with a role field,
supporting analysts who work across multiple client accounts.
"""
from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import BaseModel

User = get_user_model()


class Organization(BaseModel):
    """
    A client company whose emissions data we manage.

    This is the root of our multi-tenant hierarchy:
    Organization -> Facility -> ActivityRecord

    The egrid_subregion field is critical for Scope 2 calculations.
    We default to the organization's primary region, but individual facilities
    can override this (e.g., a company with plants in Texas and California).
    """
    name = models.CharField(
        max_length=255,
        help_text="Legal name of the client company."
    )
    slug = models.SlugField(
        unique=True,
        help_text="URL-safe identifier. Auto-generated from name."
    )

    # Default eGRID subregion for Scope 2 location-based method
    # eGRID has 26 subregions covering the US. For non-US orgs, we use country-level factors.
    egrid_subregion = models.CharField(
        max_length=10,
        blank=True,
        help_text="Default EPA eGRID subregion code (e.g., 'RFCW', 'CAMX'). Used for location-based Scope 2."
    )

    # ISO 3166-1 alpha-2 country code for international factor selection
    country = models.CharField(
        max_length=2,
        default="US",
        help_text="ISO-3166 country code. Determines which emission factor set to use."
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Soft-disable an organization without deleting their historical data."
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name


class UserOrganization(BaseModel):
    """
    Many-to-many link between Users and Organizations with role-based access.

    Roles:
    - admin: Full access, can manage users and organization settings
    - analyst: Can review and approve activity records, cannot delete organizations
    - viewer: Read-only access for auditors or executives

    A user can belong to multiple organizations (common for consulting firms).
    """
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("analyst", "Analyst"),
        ("viewer", "Viewer"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
        help_text="The user who has access to the organization."
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="user_memberships",
        help_text="The organization the user has access to."
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="viewer",
        help_text="Access level within this organization."
    )

    # Track who added this user (important for audit)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_members",
        help_text="User who granted access to this organization."
    )

    class Meta:
        unique_together = ["user", "organization"]
        verbose_name = "User Organization Membership"
        verbose_name_plural = "User Organization Memberships"

    def __str__(self):
        return f"{self.user.email} -> {self.organization.name} ({self.role})"
