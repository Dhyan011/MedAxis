from django.urls import path

from .views import MappingByPatientOrIdView, MappingListCreateView

urlpatterns = [
    path("mappings/", MappingListCreateView.as_view(), name="mapping-list"),
    path("mappings/<int:object_id>/", MappingByPatientOrIdView.as_view(), name="mapping-by-id"),
]
