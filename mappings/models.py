from django.db import models

from doctors.models import Doctor
from patients.models import Patient


class PatientDoctorMapping(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="doctor_mappings",
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="patient_mappings",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("patient", "doctor"),
                name="unique_patient_doctor_mapping",
            )
        ]

    def __str__(self):
        return f"{self.patient} → {self.doctor}"
