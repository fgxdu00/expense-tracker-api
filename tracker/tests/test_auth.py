from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

User = get_user_model()

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/auth/me/"


class AuthTests(APITestCase):
    def register(self, **overrides):
        payload = {
            "username": "fuad",
            "email": "fuad@example.com",
            "password": "correct-horse-battery",
        }
        payload.update(overrides)
        return self.client.post(REGISTER_URL, payload, format="json")

    def test_register_returns_token_and_user(self):
        response = self.register()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["username"], "fuad")
        self.assertTrue(Token.objects.filter(key=response.data["token"]).exists())
        self.assertNotIn("password", response.data["user"])

    def test_register_rejects_duplicate_username(self):
        self.register()
        response = self.register(email="other@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_register_rejects_duplicate_email_ignoring_case(self):
        self.register()
        response = self.register(username="another", email="FUAD@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_rejects_weak_password(self):
        response = self.register(password="12345678")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_requires_email(self):
        response = self.register(email="")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_login_with_valid_credentials(self):
        self.register()
        response = self.client.post(
            LOGIN_URL,
            {"username": "fuad", "password": "correct-horse-battery"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_login_with_wrong_password(self):
        self.register()
        response = self.client.post(
            LOGIN_URL,
            {"username": "fuad", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_requires_authentication(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_with_token(self):
        token = self.register().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "fuad")

    def test_logout_invalidates_token(self):
        token = self.register().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
