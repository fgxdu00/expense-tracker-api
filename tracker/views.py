from decimal import Decimal

from django.db.models import Count, Sum
from rest_framework import generics, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ExpenseFilter
from .models import Category, Expense
from .serializers import (
    CategorySerializer,
    ExpenseSerializer,
    RegisterSerializer,
    UserSerializer,
)

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(value):
    return str((value or ZERO).quantize(CENT))


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    filterset_class = ExpenseFilter
    search_fields = ["description", "category__name"]
    ordering_fields = ["date", "amount", "created_at"]

    def get_queryset(self):
        return Expense.objects.filter(owner=self.request.user).select_related("category")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        queryset = self.filter_queryset(self.get_queryset()).order_by()
        totals = queryset.aggregate(total=Sum("amount"), count=Count("id"))
        rows = (
            queryset.values("category_id", "category__name")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total", "category__name")
        )
        by_category = [
            {
                "category": row["category_id"],
                "name": row["category__name"] or "Uncategorized",
                "total": money(row["total"]),
                "count": row["count"],
            }
            for row in rows
        ]
        return Response(
            {
                "total": money(totals["total"]),
                "count": totals["count"],
                "by_category": by_category,
            }
        )
