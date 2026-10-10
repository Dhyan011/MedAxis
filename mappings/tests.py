from django.db import IntegrityError, transaction
import secrets

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from doctors.models import Doctor
from patients.models import Patient
from .models import PatientDoctorMapping


class MappingApiTests(APITestCase):
    def setUp(self):
        password = secrets.token_urlsafe(32) + "A1!"
        self.owner = User.objects.create_user(
            email="map-owner@example.com", name="Owner", password=password
        )
        self.other = User.objects.create_user(
            email="map-other@example.com", name="Other", password=password
        )
        self.client.force_authenticate(self.owner)
        self.patient = Patient.objects.create(
            created_by=self.owner,
            name="Owned Patient",
            age=30,
            gender=Patient.Gender.OTHER,
            phone="555-0100",
            address="1 Main Street",
        )
        self.other_patient = Patient.objects.create(
            created_by=self.other,
            name="Other Patient",
            age=31,
            gender=Patient.Gender.FEMALE,
            phone="555-0101",
            address="2 Main Street",
        )
        self.doctor = self.make_doctor("first@example.com", "Dr. First")
        self.second_doctor = self.make_doctor("second@example.com", "Dr. Second")
        self.list_url = reverse("mapping-list")

    def make_doctor(self, email, name):
        return Doctor.objects.create(
            created_by=self.owner,
            name=name,
            specialization="General Practice",
            email=email,
            phone="555-0110",
            experience_years=8,
        )

    def item_url(self, identifier):
        return reverse("mapping-by-id", kwargs={"object_id": identifier})

    def mapping(self, patient=None, doctor=None):
        return PatientDoctorMapping.objects.create(
            patient=patient or self.patient,
            doctor=doctor or self.doctor,
        )

    def test_create_assignment(self):
        response = self.client.post(
            self.list_url,
            {"patient_id": self.patient.pk, "doctor_id": self.doctor.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient"], self.patient.pk)
        self.assertEqual(response.data["doctor"], self.doctor.pk)

    def test_list_contains_only_callers_patient_mappings(self):
        own = self.mapping()
        self.mapping(patient=self.other_patient, doctor=self.second_doctor)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual([row["id"] for row in response.data], [own.pk])

    def test_get_patient_returns_assigned_doctors(self):
        self.mapping()
        self.mapping(doctor=self.second_doctor)
        response = self.client.get(self.item_url(self.patient.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({row["id"] for row in response.data}, {self.doctor.pk, self.second_doctor.pk})

    def test_delete_mapping_owned_by_caller(self):
        mapping = self.mapping()
        response = self.client.delete(self.item_url(mapping.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PatientDoctorMapping.objects.filter(pk=mapping.pk).exists())

    def test_duplicate_assignment_returns_400(self):
        self.mapping()
        response = self.client.post(
            self.list_url,
            {"patient_id": self.patient.pk, "doctor_id": self.doctor.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already assigned", str(response.data))

    def test_nonexistent_or_unowned_patient_is_a_non_disclosing_400(self):
        foreign = self.client.post(
            self.list_url,
            {"patient_id": self.other_patient.pk, "doctor_id": self.doctor.pk},
            format="json",
        )
        missing = self.client.post(
            self.list_url,
            {"patient_id": 999999, "doctor_id": self.doctor.pk},
            format="json",
        )
        self.assertEqual(foreign.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(foreign.data, missing.data)

    def test_nonexistent_doctor_is_400(self):
        response = self.client.post(
            self.list_url,
            {"patient_id": self.patient.pk, "doctor_id": 999999},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("doctor_id", response.data)

    def test_foreign_patient_get_and_mapping_delete_return_404(self):
        foreign_mapping = self.mapping(patient=self.other_patient, doctor=self.second_doctor)
        self.assertEqual(self.client.get(self.item_url(self.other_patient.pk)).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(self.item_url(foreign_mapping.pk)).status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(PatientDoctorMapping.objects.filter(pk=foreign_mapping.pk).exists())

    def test_missing_patient_and_mapping_return_404(self):
        self.assertEqual(self.client.get(self.item_url(999999)).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(self.item_url(999999)).status_code, status.HTTP_404_NOT_FOUND)

    def test_all_mapping_endpoints_require_authentication(self):
        mapping = self.mapping()
        self.client.force_authenticate(user=None)
        responses = (
            self.client.get(self.list_url),
            self.client.post(self.list_url, {"patient_id": self.patient.pk, "doctor_id": self.second_doctor.pk}, format="json"),
            self.client.get(self.item_url(self.patient.pk)),
            self.client.delete(self.item_url(mapping.pk)),
        )
        self.assertTrue(all(r.status_code == status.HTTP_401_UNAUTHORIZED for r in responses))

    def test_database_constraint_and_cascade_deletes(self):
        mapping = self.mapping()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        self.patient.delete()
        self.assertFalse(PatientDoctorMapping.objects.filter(pk=mapping.pk).exists())

        another_patient = Patient.objects.create(
            created_by=self.owner,
            name="Cascade Patient",
            age=25,
            gender=Patient.Gender.MALE,
            phone="555-0111",
            address="3 Main Street",
        )
        doctor_mapping = PatientDoctorMapping.objects.create(
            patient=another_patient, doctor=self.second_doctor
        )
        self.second_doctor.delete()
        self.assertFalse(PatientDoctorMapping.objects.filter(pk=doctor_mapping.pk).exists())
