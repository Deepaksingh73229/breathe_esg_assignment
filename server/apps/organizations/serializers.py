"""
Organization Serializers.
"""
from rest_framework import serializers
from apps.organizations.models import Organization, UserOrganization
from django.contrib.auth import get_user_model

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organisation create / update."""

    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "egrid_subregion", "country",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrganizationRegisterSerializer(serializers.Serializer):
    """
    Compound serializer to create an organization and its first admin user.
    """
    # Organization fields
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField()
    country = serializers.CharField(max_length=2, default="US")
    egrid_subregion = serializers.CharField(max_length=10, required=False, allow_blank=True)

    # Admin User fields
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True)
    admin_first_name = serializers.CharField(max_length=150)
    admin_last_name = serializers.CharField(max_length=150)

    def validate_admin_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_slug(self, value):
        if Organization.objects.filter(slug=value).exists():
            raise serializers.ValidationError("An organization with this slug already exists.")
        return value


class OrganizationDetailSerializer(serializers.ModelSerializer):
    """
    Detail serializer that includes membership and facility counts.

    Note: TenantModel uses related_name="%(class)s_set", which Django expands
    to "facility_set" for the Facility model (lowercase class name + "_set").
    """
    member_count = serializers.IntegerField(
        source="user_memberships.count", read_only=True
    )
    # Django expands %(class)s → "facility" for the Facility model
    facility_count = serializers.IntegerField(
        source="facility_set.count", read_only=True
    )

    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "egrid_subregion", "country",
            "is_active", "member_count", "facility_count",
            "created_at", "updated_at",
        ]


class UserOrganizationSerializer(serializers.ModelSerializer):
    """Serializer for organisation membership records."""
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = UserOrganization
        fields = [
            "id", "user", "user_email", "user_name",
            "organization", "organization_name",
            "role", "role_display", "invited_by", "created_at",
        ]

    def get_user_name(self, obj):
        if obj.user:
            return (
                f"{obj.user.first_name} {obj.user.last_name}".strip()
                or obj.user.email
            )
        return ""