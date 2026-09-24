from rest_framework.routers import DefaultRouter

from .views import PrisonerViewSet, SkillViewSet

router = DefaultRouter()
router.register("skills", SkillViewSet, basename="skill")
router.register("", PrisonerViewSet, basename="prisoner")

urlpatterns = router.urls
