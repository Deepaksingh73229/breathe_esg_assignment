"""
Activity Record API endpoints.
"""
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"", views.ActivityRecordViewSet, basename="activity")

urlpatterns = router.urls
