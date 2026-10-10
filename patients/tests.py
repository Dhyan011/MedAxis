import secrets

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Patient


class PatientApiTests(APITestCase):
    def setUp(self):
        password = secrets.token_urlsafe(32) + "A1!"
        self.owner = User.objects.create_user(
            email="owner@example.com", name="Owner", password=password
        )
        self.other = User.objects.create_user(
            email="other@example.com", name="Other", password=password
        )
        self.client.force_authenticate(self.owner)
        self.list_url = reverse("patient-list")
        self.patient = Patient.objects.create(
            created_by=self.owner,
            name="Alex Patient",
            age=35,
            gender=Patient.Gender.OTHER,
            phone="+1-555-0100",
            address="10 Main Street",
        )
        self.other_patient = Patient.objects.create(
            created_by=self.other,
            name="Private Patient",
            age=40,
            gender=Patient.Gender.FEMALE,
            phone="+1-555-0101",
            address="20 Main Street",
        )

    def detail_url(self, patient):
        return reverse("patient-detail", kwargs={"pk": patient.pk})

    def valid_payload(self, **overrides):
        data = {
            "name": "Casey New",
            "age": 21,
            "gender": "F",
            "phone": "555-0199",
            "address": "99 New Road",
            "medical_history": "",
        }
        data.update(overrides)
        return data

    def test_create_sets_owner_from_request_user(self):
        response = self.client.post(
            self.list_url,
            self.valid_payload(created_by=self.other.pk),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Patient.objects.get(pk=response.data["id"])
        self.assertEqual(created.created_by, self.owner)
        self.assertEqual(response.data["created_by"], self.owner.pk)

    def test_put_cannot_change_patient_owner(self):
        response = self.client.put(
            self.detail_url(self.patient),
            self.valid_payload(created_by=self.other.pk),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.created_by, self.owner)

    def test_list_returns_plain_array_of_only_owned_patients(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual([row["id"] for row in response.data], [self.patient.pk])

    def test_retrieve_update_and_delete_owned_patient(self):
        detail = self.detail_url(self.patient)
        self.assertEqual(self.client.get(detail).status_code, status.HTTP_200_OK)
        update = self.client.put(detail, self.valid_payload(name="Updated Patient"), format="json")
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.name, "Updated Patient")
        patched = self.client.patch(detail, {"age": 36}, format="json")
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.age, 36)
        deleted = self.client.delete(detail)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(pk=self.patient.pk).exists())

    def test_invalid_age_name_and_types_return_400(self):
        invalid_payloads = (
            self.valid_payload(age=-1),
            self.valid_payload(age=131),
            self.valid_payload(name=""),
            self.valid_payload(age="not-a-number"),
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(self.list_url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_users_patient_is_404_for_get_put_and_delete(self):
        detail = self.detail_url(self.other_patient)
        self.assertEqual(self.client.get(detail).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.put(detail, self.valid_payload(), format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_patient_is_404(self):
        detail = reverse("patient-detail", kwargs={"pk": 999999})
        self.assertEqual(self.client.get(detail).status_code, status.HTTP_404_NOT_FOUND)

    def test_patient_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)
        responses = [
            self.client.get(self.list_url),
            self.client.post(self.list_url, self.valid_payload(), format="json"),
            self.client.get(self.detail_url(self.patient)),
            self.client.put(self.detail_url(self.patient), self.valid_payload(), format="json"),
            self.client.delete(self.detail_url(self.patient)),
        ]
        self.assertTrue(all(r.status_code == status.HTTP_401_UNAUTHORIZED for r in responses))
