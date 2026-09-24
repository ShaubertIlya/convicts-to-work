from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BiometryCallbackView, EmploymentContractViewSet

router = DefaultRouter()
router.register("", EmploymentContractViewSet, basename="contract")

urlpatterns = [path("biometry/callback/", BiometryCallbackView.as_view(), name="biometry-callback")]
urlpatterns += router.urls
