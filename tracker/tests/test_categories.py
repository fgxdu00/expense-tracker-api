from rest_framework import status

from tracker.models import Category, Expense

from .helpers import AuthenticatedTestCase

URL = "/api/categories/"


class CategoryTests(AuthenticatedTestCase):
    def test_create_category(self):
        response = self.client.post(URL, {"name": "Food"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.get().owner, self.user)

    def test_duplicate_name_is_rejected_ignoring_case(self):
        Category.objects.create(owner=self.user, name="Food")
        response = self.client.post(URL, {"name": "food"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_name_is_allowed_for_different_users(self):
        Category.objects.create(owner=self.other, name="Food")
        response = self.client.post(URL, {"name": "Food"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_contains_only_own_categories(self):
        Category.objects.create(owner=self.user, name="Food")
        Category.objects.create(owner=self.other, name="Secret")
        response = self.client.get(URL)
        names = [item["name"] for item in response.data["results"]]
        self.assertEqual(names, ["Food"])

    def test_cannot_read_or_change_foreign_category(self):
        foreign = Category.objects.create(owner=self.other, name="Secret")
        detail = f"{URL}{foreign.pk}/"
        self.assertEqual(self.client.get(detail).status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.patch(detail, {"name": "Hacked"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_404_NOT_FOUND)

    def test_rename_keeps_unique_check_working(self):
        category = Category.objects.create(owner=self.user, name="Food")
        response = self.client.patch(f"{URL}{category.pk}/", {"name": "Food"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_deleting_category_keeps_expenses(self):
        category = Category.objects.create(owner=self.user, name="Food")
        expense = Expense.objects.create(owner=self.user, category=category, amount="5.00")
        response = self.client.delete(f"{URL}{category.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        expense.refresh_from_db()
        self.assertIsNone(expense.category)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_401_UNAUTHORIZED)
