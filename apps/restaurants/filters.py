import django_filters
from .models import Restaurants, MenuItem


class RestaurantFilter(django_filters.FilterSet):

    # ── MultipleChoiceFilter — handles ?cuisine_type=PIZZA&cuisine_type=BURGER
    cuisine_type = django_filters.MultipleChoiceFilter(
        choices=Restaurants.CuisineType.choices,
        # conjoined=False → OR logic (PIZZA or BURGER)
        conjoined=False,
    )

    # ── Exact filters ──────────────────────────────────────────────────────
    city     = django_filters.CharFilter(lookup_expr="iexact")
    # iexact = case insensitive — "delhi" matches "Delhi"
    is_open  = django_filters.BooleanFilter()

    # ── Range filters — ?min_rating=4.0 ───────────────────────────────────
    min_rating   = django_filters.NumberFilter(field_name="average_rating", lookup_expr="gte")
    max_delivery_time = django_filters.NumberFilter(field_name="avg_preparing_time", lookup_expr="lte")

    class Meta:
        model  = Restaurants
        fields = ["cuisine_type", "city", "is_open"]


class MenuItemFilter(django_filters.FilterSet):

    # ── Multi-value category filter ────────────────────────────────────────
    # ?category=Starters&category=Burgers
    category = django_filters.CharFilter(
        field_name="category__name",
        lookup_expr="iexact",
    )

    # ── Price range ────────────────────────────────────────────────────────
    # ?min_price=50&max_price=200
    min_price = django_filters.NumberFilter(field_name="base_price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="base_price", lookup_expr="lte")

    # ── Boolean filters ────────────────────────────────────────────────────
    is_veg        = django_filters.BooleanFilter()
    is_available  = django_filters.BooleanFilter()
    is_bestseller = django_filters.BooleanFilter()

    class Meta:
        model  = MenuItem
        fields = ["is_veg", "is_available", "is_bestseller"]