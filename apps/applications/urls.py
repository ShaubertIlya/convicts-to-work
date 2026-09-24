from rest_framework.routers import DefaultRouter

from .views import JobApplicationViewSet, ScreeningViewSet

router = DefaultRouter()
router.register("screenings", ScreeningViewSet, basename="screening")
router.register("", JobApplicationViewSet, basename="application")

urlpatterns = router.urls
