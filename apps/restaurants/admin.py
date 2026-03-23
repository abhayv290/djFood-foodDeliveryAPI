from django.contrib import admin
from .models import MenuItem,Restaurants,Category,MenuItemVariants
# Register your models here.

#for inside menuitems
class MenuItemVariantInline(admin.TabularInline):
    model = MenuItemVariants
    extra=1
    fields = ('name','price','is_available',)

#for inside category
class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra=1
    fields =('name','base_price','is_veg','is_available','is_bestseller')
    show_change_link=True

#for inside restaurants
class CategoryInline(admin.TabularInline):
    model = Category
    extra=1
    fields=('name','order')


@admin.register(Restaurants)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name','cuisine_type','city','is_active','is_open','average_rating','total_ratings')
    list_filter = ('cuisine_type','is_active','is_open','average_rating')
    list_editable = ('is_open','is_active',)
    search_fields = ('name','cuisine_type','city','owner__email')
    ordering = ('-created_at',)

    list_select_related = ('owner',)
    inlines = [CategoryInline]

  # ── fieldsets organize the edit page into sections 
    fieldsets = (
        ("Basic info",    {"fields": ("owner", "name", "description", "cuisine_type", "image")}),
        ("Location",      {"fields": ("address","city","pincode", "phone", "lat", "long")}),
        ("Delivery",      {"fields": ("min_order_amount","avg_preparing_time")}),
        ("Status",        {"fields": ("is_active", "is_open")}),
        ("Stats",         {"fields": ("average_rating", "total_ratings"), "classes": ("collapse",)}),
        # ↑ collapse — stats section hidden by default, click to expand
    )
    readonly_fields = ["average_rating", "total_ratings"]




@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display=('restaurant','name','order')
    list_editable=('order',)
    search_fields =('restaurant__name','name')
    ordering = ('restaurant','order')
    inlines=[MenuItemInline]




@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name','category__name','base_price','is_veg','is_available','is_bestseller')
    list_editable = ('is_veg','is_bestseller','is_available')
    list_filter = ('is_veg','is_available','is_bestseller')
    search_fields = ('name','category__name','category__restaurant__name')
    ordering=('order','category')
    inlines = [MenuItemVariantInline]

@admin.register(MenuItemVariants)
class MenuItemVariantAdmin(admin.ModelAdmin):
    list_display = ('name','menu_item__name','price','is_available',)
    list_editable = ('is_available',)
    list_filter = ('is_available',)
    search_fields = ('name','menu_item__name',)
