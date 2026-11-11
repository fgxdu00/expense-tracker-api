from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class AuthenticatedTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", "alice@example.com", "s3cure-pass-91")
        self.other = User.objects.create_user("bob", "bob@example.com", "s3cure-pass-92")
        self.client.force_authenticate(self.user)
