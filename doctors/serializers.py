from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    experience_years = serializers.IntegerField(min_value=0, max_value=80)

    class Meta:
        model = Doctor
        fields = (
            "id",
            "created_by",
            "name",
            "specialization",
            "email",
            "phone",
            "experience_years",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def validate_email(self, value):
        normalized = value.strip().lower()
        duplicates = Doctor.objects.filter(email__iexact=normalized)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A doctor with this email already exists.")
        return normalized

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"email": "A doctor with this email already exists."}
            ) from exc
