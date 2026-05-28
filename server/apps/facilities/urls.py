"""
Facility API endpoints.
"""
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"", views.FacilityViewSet, basename="facility")

urlpatterns = router.urls
