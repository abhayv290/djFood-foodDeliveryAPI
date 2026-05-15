from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,CustomerAddress,CustomerProfile,RestaurantOwnerProfile,DeliveryAgentProfile,EmailVerificationToken
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email','name','role','is_active','is_email_verified','is_phone_verified','date_joined')
    list_filter = ('role','is_active' ,'is_phone_verified','is_email_verified')
    search_fields = ('email' ,'name' , 'phone')
    ordering = ('-date_joined',)

    fieldsets =(
        (None, {'fields' : ('email','password')}),
        ('Personal Info' , {'fields' :('name','phone','role')}),
        ('Verification' ,{'fields' : ('is_phone_verified','is_email_verified')}),
        ('Permissions' , {'fields' : ('is_active' , 'is_staff' , 'is_superuser','groups','user_permissions') }),
        ('Dates' , {'fields' : ('date_joined' ,'last_login')}),
    )
    
    add_fieldsets = (
        (None , {
            'classes' :('wide' ,),
            'fields': ('email','name' , 'phone' , 'role' , 'password' ,'password2'),
        })
    )
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user' , 'total_orders' , 'loyalty_points','is_vegetarian')
    search_fields = ('user__email' , 'user__name')
    list_filter = ('is_vegetarian',)    

@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display=('customer','label','pincode','is_default')
    list_filter =('label',)
    search_fields=('pincode','formatted_address')


@admin.register(RestaurantOwnerProfile)
class RestaurantOwnerProfileAdmin(admin.ModelAdmin):
    list_display = ('user' , 'is_verified' ,)
    search_fields = ('user__email' , 'user__name')
    list_filter = ('is_verified',)

@admin.register(DeliveryAgentProfile)
class DeliveryAgentProfileAdmin(admin.ModelAdmin):
    list_display = ('user' , 'vehicle_type' ,'status' , 'total_deliveries' ,'average_rating', 'is_verified' ,)
    search_fields = ('user__email' , 'user__name')
    list_filter = ('is_verified',)


@admin.register(EmailVerificationToken)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'token','expires_at' ,'created_at')
    search_fields= ('user__name','user__email')
    
    readonly_fields = ('token','created_at')


admin.site.site_header = 'FoodRevolut - Food Delivery API'
admin.site.site_title = 'FoodRevolut Admin Panel'
admin.site.index_title = 'Welcome to FoodRevolut Administration'