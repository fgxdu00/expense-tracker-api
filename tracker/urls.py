from django.urls import include, path
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ExpenseViewSet, LogoutView, MeView, RegisterView

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("expenses", ExpenseViewSet, basename="expense")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", ObtainAuthToken.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
