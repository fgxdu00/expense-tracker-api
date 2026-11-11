from rest_framework import status

from tracker.models import Category, Expense

from .helpers import AuthenticatedTestCase

URL = "/api/expenses/"
SUMMARY_URL = "/api/expenses/summary/"


class ExpenseTestCase(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        self.food = Category.objects.create(owner=self.user, name="Food")
        self.transport = Category.objects.create(owner=self.user, name="Transport")
        self.foreign_category = Category.objects.create(owner=self.other, name="Secret")

    def add(self, amount, date, category=None, description="", owner=None):
        return Expense.objects.create(
            owner=owner or self.user,
            category=category,
            amount=amount,
            date=date,
            description=description,
        )


class ExpenseCrudTests(ExpenseTestCase):
    def test_create_expense(self):
        payload = {
            "amount": "12.50",
            "description": "Lunch",
            "date": "2026-03-10",
            "category": self.food.pk,
        }
        response = self.client.post(URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["category_name"], "Food")
        self.assertEqual(Expense.objects.get().owner, self.user)

    def test_create_without_category(self):
        response = self.client.post(URL, {"amount": "3.00", "date": "2026-03-10"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["category"])
        self.assertIsNone(response.data["category_name"])

    def test_date_defaults_to_today(self):
        response = self.client.post(URL, {"amount": "3.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["date"])

    def test_cannot_use_foreign_category(self):
        payload = {"amount": "5.00", "category": self.foreign_category.pk}
        response = self.client.post(URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

    def test_rejects_zero_and_negative_amounts(self):
        for amount in ("0", "0.00", "-4.00"):
            response = self.client.post(URL, {"amount": amount}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, amount)

    def test_rejects_too_many_decimal_places(self):
        response = self.client.post(URL, {"amount": "1.234"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_and_delete(self):
        expense = self.add("10.00", "2026-03-01", self.food)
        detail = f"{URL}{expense.pk}/"
        response = self.client.patch(detail, {"amount": "11.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["amount"], "11.00")
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Expense.objects.exists())

    def test_foreign_expenses_are_hidden(self):
        foreign = self.add("99.00", "2026-03-01", owner=self.other)
        detail = f"{URL}{foreign.pk}/"
        self.assertEqual(self.client.get(detail).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(URL).data["count"], 0)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_401_UNAUTHORIZED)


class ExpenseListTests(ExpenseTestCase):
    def setUp(self):
        super().setUp()
        self.add("10.00", "2026-01-05", self.food, "Groceries")
        self.add("40.00", "2026-02-10", self.transport, "Monthly bus pass")
        self.add("25.00", "2026-02-20", self.food, "Restaurant")
        self.add("5.00", "2026-03-01", None, "Coffee")

    def amounts(self, query=""):
        response = self.client.get(f"{URL}{query}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [item["amount"] for item in response.data["results"]]

    def test_default_order_is_newest_first(self):
        self.assertEqual(self.amounts(), ["5.00", "25.00", "40.00", "10.00"])

    def test_filter_by_category(self):
        self.assertEqual(self.amounts(f"?category={self.food.pk}"), ["25.00", "10.00"])

    def test_foreign_category_filter_is_rejected(self):
        response = self.client.get(f"{URL}?category={self.foreign_category.pk}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_date_range(self):
        self.assertEqual(
            self.amounts("?date_from=2026-02-01&date_to=2026-02-28"),
            ["25.00", "40.00"],
        )

    def test_filter_by_amount_range(self):
        self.assertEqual(self.amounts("?min_amount=10&max_amount=25"), ["25.00", "10.00"])

    def test_search_description_and_category_name(self):
        self.assertEqual(self.amounts("?search=bus"), ["40.00"])
        self.assertEqual(self.amounts("?search=transport"), ["40.00"])

    def test_ordering_by_amount(self):
        self.assertEqual(self.amounts("?ordering=-amount"), ["40.00", "25.00", "10.00", "5.00"])

    def test_pagination(self):
        for index in range(25):
            self.add("1.00", "2026-04-01", description=f"Item {index}")
        first = self.client.get(URL).data
        self.assertEqual(first["count"], 29)
        self.assertEqual(len(first["results"]), 20)
        self.assertIsNotNone(first["next"])
        second = self.client.get(first["next"]).data
        self.assertEqual(len(second["results"]), 9)


class ExpenseSummaryTests(ExpenseTestCase):
    def setUp(self):
        super().setUp()
        self.add("10.00", "2026-01-05", self.food)
        self.add("25.50", "2026-02-20", self.food)
        self.add("40.00", "2026-02-10", self.transport)
        self.add("5.00", "2026-03-01")
        self.add("500.00", "2026-02-15", owner=self.other)

    def test_summary_for_everything(self):
        response = self.client.get(SUMMARY_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], "80.50")
        self.assertEqual(response.data["count"], 4)
        names = [row["name"] for row in response.data["by_category"]]
        self.assertEqual(names, ["Transport", "Food", "Uncategorized"])
        food = response.data["by_category"][1]
        self.assertEqual(food["total"], "35.50")
        self.assertEqual(food["count"], 2)
        self.assertEqual(food["category"], self.food.pk)

    def test_summary_respects_filters(self):
        response = self.client.get(f"{SUMMARY_URL}?date_from=2026-02-01&date_to=2026-02-28")
        self.assertEqual(response.data["total"], "65.50")
        self.assertEqual(response.data["count"], 2)

    def test_summary_without_matches(self):
        response = self.client.get(f"{SUMMARY_URL}?date_from=2030-01-01")
        self.assertEqual(response.data["total"], "0.00")
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["by_category"], [])

    def test_summary_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(SUMMARY_URL).status_code, status.HTTP_401_UNAUTHORIZED)
