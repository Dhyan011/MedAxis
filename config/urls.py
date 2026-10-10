from django.urls import include, path

urlpatterns = [
    path("api/", include("accounts.urls")),
    path("api/", include("patients.urls")),
    path("api/", include("doctors.urls")),
    path("api/", include("mappings.urls")),
]
