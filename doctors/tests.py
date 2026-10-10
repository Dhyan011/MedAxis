import secrets

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Doctor


class DoctorApiTests(APITestCase):
    def setUp(self):
        password = secrets.token_urlsafe(32) + "A1!"
        self.creator = User.objects.create_user(
            email="creator@example.com", name="Creator", password=password
        )
        self.other = User.objects.create_user(
            email="reader@example.com", name="Reader", password=password
        )
        self.client.force_authenticate(self.creator)
        self.list_url = reverse("doctor-list")
        self.doctor = Doctor.objects.create(
            created_by=self.creator,
            name="Dr. Rowan",
            specialization="Cardiology",
            email="rowan@example.com",
            phone="555-0110",
            experience_years=12,
        )

    def detail_url(self, doctor=None, pk=None):
        return reverse("doctor-detail", kwargs={"pk": pk if pk is not None else doctor.pk})

    def valid_payload(self, **overrides):
        data = {
            "name": "Dr. New",
            "specialization": "Pediatrics",
            "email": "newdoctor@example.com",
            "phone": "555-0190",
            "experience_years": 5,
        }
        data.update(overrides)
        return data

    def test_create_ignores_client_creator_id(self):
        response = self.client.post(
            self.list_url,
            self.valid_payload(created_by=self.other.pk),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doctor = Doctor.objects.get(pk=response.data["id"])
        self.assertEqual(doctor.created_by, self.creator)

    def test_authenticated_users_can_list_and_retrieve_all_doctors(self):
        self.client.force_authenticate(self.other)
        listing = self.client.get(self.list_url)
        detail = self.client.get(self.detail_url(self.doctor))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertIsInstance(listing.data, list)
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(detail.status_code, status.HTTP_200_OK)

    def test_creator_can_update_and_delete(self):
        detail = self.detail_url(self.doctor)
        updated = self.client.put(detail, self.valid_payload(name="Dr. Updated"), format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.name, "Dr. Updated")
        patched = self.client.patch(detail, {"phone": "555-0122"}, format="json")
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.phone, "555-0122")
        deleted = self.client.delete(detail)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Doctor.objects.filter(pk=self.doctor.pk).exists())

    def test_non_creator_cannot_update_or_delete(self):
        self.client.force_authenticate(self.other)
        detail = self.detail_url(self.doctor)
        updated = self.client.put(detail, self.valid_payload(), format="json")
        deleted = self.client.delete(detail)
        self.assertEqual(updated.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(deleted.status_code, status.HTTP_403_FORBIDDEN)

    def test_validation_rejects_missing_fields_bad_values_and_duplicate_email(self):
        bad_responses = (
            self.client.post(self.list_url, self.valid_payload(name=""), format="json"),
            self.client.post(self.list_url, self.valid_payload(experience_years=-1), format="json"),
            self.client.post(self.list_url, self.valid_payload(email="bad"), format="json"),
            self.client.post(self.list_url, {"name": "Incomplete"}, format="json"),
            self.client.post(self.list_url, self.valid_payload(email="ROWAN@EXAMPLE.COM"), format="json"),
        )
        self.assertTrue(all(r.status_code == status.HTTP_400_BAD_REQUEST for r in bad_responses))

    def test_missing_doctor_is_404(self):
        self.assertEqual(self.client.get(self.detail_url(pk=999999)).status_code, status.HTTP_404_NOT_FOUND)

    def test_doctor_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)
        responses = (
            self.client.get(self.list_url),
            self.client.post(self.list_url, self.valid_payload(), format="json"),
            self.client.get(self.detail_url(self.doctor)),
            self.client.put(self.detail_url(self.doctor), self.valid_payload(), format="json"),
            self.client.delete(self.detail_url(self.doctor)),
        )
        self.assertTrue(all(r.status_code == status.HTTP_401_UNAUTHORIZED for r in responses))
