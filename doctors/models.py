from django.conf import settings
from django.db import models


class Doctor(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctors_created",
    )
    name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32)
    experience_years = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.specialization})"
