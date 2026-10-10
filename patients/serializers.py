from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    age = serializers.IntegerField(min_value=0, max_value=130)

    class Meta:
        model = Patient
        fields = (
            "id",
            "created_by",
            "name",
            "age",
            "gender",
            "phone",
            "address",
            "medical_history",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")
