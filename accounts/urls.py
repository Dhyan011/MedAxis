from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from .views import RegisterView


class PublicTokenObtainPairView(TokenObtainPairView):
    permission_classes = (AllowAny,)


urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", PublicTokenObtainPairView.as_view(), name="token_obtain_pair"),
]
