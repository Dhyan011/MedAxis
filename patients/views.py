from rest_framework.viewsets import ModelViewSet

from .models import Patient
from .serializers import PatientSerializer


class PatientViewSet(ModelViewSet):
    serializer_class = PatientSerializer

    def get_queryset(self):
        return Patient.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
