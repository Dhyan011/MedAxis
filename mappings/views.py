from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from doctors.models import Doctor
from doctors.serializers import DoctorSerializer
from patients.models import Patient
from .models import PatientDoctorMapping
from .serializers import MappingCreateSerializer, MappingReadSerializer


class MappingListCreateView(APIView):
    def get(self, request):
        mappings = PatientDoctorMapping.objects.filter(
            patient__created_by=request.user
        ).select_related("patient", "doctor")
        return Response(MappingReadSerializer(mappings, many=True).data)

    def post(self, request):
        serializer = MappingCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        mapping = serializer.save()
        return Response(
            MappingReadSerializer(mapping).data,
            status=status.HTTP_201_CREATED,
        )


class MappingByPatientOrIdView(APIView):
    def get(self, request, object_id):
        patient = get_object_or_404(
            Patient.objects.filter(created_by=request.user), pk=object_id
        )
        doctors = Doctor.objects.filter(
            patient_mappings__patient=patient
        ).select_related("created_by").distinct()
        return Response(DoctorSerializer(doctors, many=True).data)

    def delete(self, request, object_id):
        # The shared route interprets this segment as a mapping ID for DELETE.
        mapping = get_object_or_404(
            PatientDoctorMapping.objects.select_related("patient").filter(
                patient__created_by=request.user
            ),
            pk=object_id,
        )
        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
