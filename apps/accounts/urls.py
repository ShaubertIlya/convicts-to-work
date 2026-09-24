from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BusinessRegistrationView, EnbekUserViewSet, LoginView, LogoutView, MeView

router = DefaultRouter()
router.register("users", EnbekUserViewSet, basename="enbek-user")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("register/", BusinessRegistrationView.as_view(), name="business-register"),
]
urlpatterns += router.urls
