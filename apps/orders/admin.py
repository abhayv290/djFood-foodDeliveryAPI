from django.contrib import admin

from .models import Order, OrderItem, OrderStatusHistory,Cart,CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('menu_item','variant','quantity','unit_price','subtotal')
    readonly_fields = ('menu_item','variant','quantity','unit_price','subtotal')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('customer', 'restaurant','item_count','subtotal', 'created_at', 'updated_at')
    search_fields = ('customer__email','restaurant__name')
    inlines = [CartItemInline]
    readonly_fields = ('customer','restaurant','item_count','subtotal')


class OrderItemInline(admin.TabularInline):
    model=OrderItem
    extra=0
    fields = ('item_name','variant_name','quantity','price','subtotal')
    readonly_fields = ('item_name','variant_name','quantity','price','subtotal')


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    fields = ('status','changed_by', 'changed_at','note')
    readonly_fields = ('status','changed_by', 'changed_at','note')
    ordering = ('-changed_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('customer','restaurant','status','payment_method','is_paid','total_amount','placed_at')
    search_fields = ('customer__email','restaurant__name')
    list_filter = ('status','is_paid','payment_method')
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    readonly_fields = ('customer','restaurant','total_amount','payment_method','is_paid','placed_at','delivery_address','delivery_fee','subtotal')
