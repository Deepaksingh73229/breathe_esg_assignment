"""
Emission Factor API endpoints.
"""
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"", views.EmissionFactorViewSet, basename="factor")

urlpatterns = router.urls
