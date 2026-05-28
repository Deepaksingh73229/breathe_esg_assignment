"""
Ingestion API URLs.
"""
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"", views.IngestionRunViewSet, basename="ingestion")

urlpatterns = router.urls