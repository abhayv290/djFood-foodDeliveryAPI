from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CartView,CartItemView,CheckoutView,AgentOrderViewSet,CustomerOrderViewSet,
    OrderStatusUpdateView,CustomerCancelOrderView,RestaurantOrderViewSet,
)

app_name = 'orders'

router = DefaultRouter()
router.register(r'orders/agents', AgentOrderViewSet, basename='agent-order')
router.register(r'orders/restaurants', RestaurantOrderViewSet, basename='restaurant-order')

urlpatterns = router.urls + [
    #cart
    path('cart/',CartView.as_view(),name='cart'),
    path('cart/items/',CartItemView.as_view(),name='cart-items'),
    path('cart/items/<uuid:pk>/',CartItemView.as_view(),name='cart-item-details'),
    #checkout
    path('orders/checkout/',CheckoutView.as_view(),name='checkout'),

    path('orders/<uuid:pk>/cancel/',CustomerCancelOrderView.as_view(),name='customer-order-cancel'),

    #status update - restaurant + agent 
    path('orders/<uuid:pk>/status/',OrderStatusUpdateView.as_view(),name='order-status-update')
]
router.register(r'orders', CustomerOrderViewSet, basename='customer-order')
urlpatterns += router.urls
