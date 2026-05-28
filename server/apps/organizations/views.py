"""
Organization API Views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from django.db import transaction
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, UserOrganization
from .serializers import (
    OrganizationSerializer, 
    OrganizationDetailSerializer, 
    UserOrganizationSerializer,
    OrganizationRegisterSerializer
)

User = get_user_model()

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

class MeView(APIView):
    """
    Returns or updates the current user's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        memberships = user.organization_memberships.select_related("organization").all()
        return Response({
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_superuser": user.is_superuser,
            "organizations": [
                {
                    "id": str(m.organization.id),
                    "name": m.organization.name,
                    "role": m.role
                } for m in memberships
            ]
        })

    def patch(self, request):
        user = request.user
        data = request.data
        
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "email" in data:
            user.email = data["email"]
            user.username = data["email"]  # Keep username in sync
            
        user.save()
        return self.get(request)

class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing organizations.

    Users can only see organizations they belong to.
    Admins can create new organizations.
    """
    queryset = Organization.objects.filter(is_active=True, is_deleted=False)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["country", "is_active"]

    def get_serializer_class(self):
        if self.action in ["retrieve", "list"]:
            return OrganizationDetailSerializer
        if self.action == "register_with_admin":
            return OrganizationRegisterSerializer
        return OrganizationSerializer

    def get_queryset(self):
        """Scope to user's organizations."""
        user_orgs = self.request.user.organization_memberships.values_list("organization_id", flat=True)
        return Organization.objects.filter(id__in=user_orgs, is_active=True, is_deleted=False)

    def perform_create(self, serializer):
        """Create org and add creator as admin."""
        org = serializer.save(created_by=self.request.user)
        UserOrganization.objects.create(
            user=self.request.user,
            organization=org,
            role="admin",
            invited_by=self.request.user,
            created_by=self.request.user,
        )
        return org

    @action(detail=False, methods=["post"])
    def register_with_admin(self, request):
        """
        Create an organization and its first admin user in a single atomic transaction.
        Available to system superadmins.
        """
        if not request.user.is_superuser:
            return Response(
                {"error": "Only system superusers can register new organizations."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            # 1. Create Organization
            org = Organization.objects.create(
                name=data["name"],
                slug=data["slug"],
                country=data["country"],
                egrid_subregion=data.get("egrid_subregion", ""),
                created_by=request.user
            )

            # 2. Create Admin User
            admin_user = User.objects.create_user(
                username=data["admin_email"],  # Using email as username for simplicity
                email=data["admin_email"],
                password=data["admin_password"],
                first_name=data["admin_first_name"],
                last_name=data["admin_last_name"]
            )

            # 3. Link User to Organization as Admin
            UserOrganization.objects.create(
                user=admin_user,
                organization=org,
                role="admin",
                invited_by=request.user,
                created_by=request.user
            )

        return Response({
            "status": "success",
            "organization": {
                "id": str(org.id),
                "name": org.name
            },
            "admin_user": {
                "id": str(admin_user.id),
                "email": admin_user.email
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def invite_member(self, request, pk=None):
        """
        Add a member to an organization by email.
        If the user doesn't exist, create an account with a temporary password.
        """
        org = self.get_object()
        
        # Check if the performing user is an admin of this organization
        membership = request.user.organization_memberships.filter(organization=org, role="admin").first()
        if not membership and not request.user.is_superuser:
            return Response(
                {"error": "Only organization admins can invite members."},
                status=status.HTTP_403_FORBIDDEN
            )

        email = request.data.get("email")
        role = request.data.get("role", "viewer")
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "first_name": first_name,
                    "last_name": last_name,
                }
            )
            
            if created:
                # Set a temporary password for new users
                temp_password = "BreatheWelcome123!" # In a real app, send an invite email with reset link
                user.set_password(temp_password)
                user.save()

            # Check if already a member
            if UserOrganization.objects.filter(user=user, organization=org).exists():
                return Response({"error": "User is already a member of this organization."}, status=status.HTTP_400_BAD_REQUEST)

            new_membership = UserOrganization.objects.create(
                user=user,
                organization=org,
                role=role,
                invited_by=request.user,
                created_by=request.user
            )

        return Response({
            "status": "invited",
            "user_id": str(user.id),
            "email": user.email,
            "role": role,
            "is_new_user": created,
            "temporary_password": temp_password if created else None
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def members(self, request, pk=None):
        """Get or add organization members."""
        org = self.get_object()

        if request.method == "GET":
            members = UserOrganization.objects.filter(organization=org, is_deleted=False)
            serializer = UserOrganizationSerializer(members, many=True)
            return Response(serializer.data)

        # POST: add member
        serializer = UserOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=org, invited_by=request.user, created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
