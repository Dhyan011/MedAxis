from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Doctor
from .serializers import DoctorSerializer


class IsCreatorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.created_by_id == request.user.id


class DoctorViewSet(ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = (IsAuthenticated, IsCreatorOrReadOnly)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
