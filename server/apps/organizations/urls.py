"""
Organization API endpoints.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"", views.OrganizationViewSet, basename="organization")

urlpatterns = [
    path("me/", views.MeView.as_view(), name="user-me"),
] + router.urls
