from django.db import IntegrityError, transaction
from rest_framework import serializers

from doctors.models import Doctor
from patients.models import Patient
from .models import PatientDoctorMapping


class MappingCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(min_value=1)
    doctor_id = serializers.IntegerField(min_value=1)

    def validate_patient_id(self, value):
        user = self.context["request"].user
        if not Patient.objects.filter(pk=value, created_by=user).exists():
            raise serializers.ValidationError("Patient is not available to this user.")
        return value

    def validate_doctor_id(self, value):
        if not Doctor.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Doctor does not exist.")
        return value

    def validate(self, attrs):
        if PatientDoctorMapping.objects.filter(
            patient_id=attrs["patient_id"], doctor_id=attrs["doctor_id"]
        ).exists():
            raise serializers.ValidationError(
                {"doctor_id": "This doctor is already assigned to this patient."}
            )
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return PatientDoctorMapping.objects.create(**validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"doctor_id": "This doctor is already assigned to this patient."}
            ) from exc


class MappingReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDoctorMapping
        fields = ("id", "patient", "doctor", "created_at")
        read_only_fields = fields
