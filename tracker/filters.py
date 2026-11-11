import django_filters

from .models import Category, Expense


def user_categories(request):
    if request is None or not request.user.is_authenticated:
        return Category.objects.none()
    return Category.objects.filter(owner=request.user)


class ExpenseFilter(django_filters.FilterSet):
    category = django_filters.ModelChoiceFilter(queryset=user_categories)
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = Expense
        fields = ["category", "date_from", "date_to", "min_amount", "max_amount"]
