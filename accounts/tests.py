import secrets

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("register")
        self.login_url = reverse("token_obtain_pair")
        self.password = secrets.token_urlsafe(32) + "A1!"

    def registration_data(self, **overrides):
        data = {
            "name": "Jamie Example",
            "email": "jamie@example.com",
            "password": self.password,
        }
        data.update(overrides)
        return data

    def test_register_normalizes_email_and_never_returns_password(self):
        response = self.client.post(
            self.register_url,
            self.registration_data(email="  Jamie@Example.COM  "),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "jamie@example.com")
        self.assertNotIn("password", response.data)
        user = User.objects.get(email="jamie@example.com")
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)

    def test_register_rejects_missing_fields(self):
        for field in ("name", "email", "password"):
            data = self.registration_data()
            data.pop(field)
            with self.subTest(field=field):
                response = self.client.post(self.register_url, data, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)

    def test_register_rejects_invalid_email(self):
        response = self.client.post(
            self.register_url,
            self.registration_data(email="not-an-email"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            self.register_url,
            self.registration_data(password=self.registration_data()["name"]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_rejects_duplicate_email_case_insensitively(self):
        self.client.post(self.register_url, self.registration_data(), format="json")
        response = self.client.post(
            self.register_url,
            self.registration_data(email="JAMIE@EXAMPLE.COM"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_login_returns_access_and_refresh_tokens(self):
        User.objects.create_user(email="jamie@example.com", name="Jamie", password=self.password)
        response = self.client.post(
            self.login_url,
            {"email": "jamie@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_wrong_password_and_unknown_email_generically(self):
        User.objects.create_user(email="jamie@example.com", name="Jamie", password=self.password)
        wrong_secret = secrets.token_urlsafe(32) + "A1!"
        wrong_password_response = self.client.post(
            self.login_url,
            {"email": "jamie@example.com", "password": wrong_secret},
            format="json",
        )
        unknown_email = self.client.post(
            self.login_url,
            {"email": "nobody@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(wrong_password_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(unknown_email.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(wrong_password_response.data, unknown_email.data)

    def test_real_jwt_authenticates_protected_patient_endpoint(self):
        User.objects.create_user(email="jamie@example.com", name="Jamie", password=self.password)
        protected_url = reverse("patient-list")
        self.assertEqual(
            self.client.get(protected_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        login = self.client.post(
            self.login_url,
            {"email": "jamie@example.com", "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.get(protected_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_invalid_bearer_token_is_rejected(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {secrets.token_urlsafe(32)}"
        )
        response = self.client.get(reverse("patient-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
