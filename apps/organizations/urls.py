from rest_framework.routers import DefaultRouter

from .views import BankViewSet, OkedCodeViewSet, OrganizationViewSet

router = DefaultRouter()
router.register("oked", OkedCodeViewSet, basename="oked")
router.register("banks", BankViewSet, basename="bank")
router.register("", OrganizationViewSet, basename="organization")
urlpatterns = router.urls
