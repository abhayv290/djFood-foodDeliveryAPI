import uuid 
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class Restaurants(models.Model):
    class CuisineType(models.TextChoices):
        NORTH_INDIAN = "NORTH_INDIAN", "North Indian"
        SOUTH_INDIAN = "SOUTH_INDIAN", "South Indian"
        CHINESE      = "CHINESE",      "Chinese"
        ITALIAN      = "ITALIAN",      "Italian"
        STREET_FOOD  = "STREET_FOOD",  "Street Food & Chaat"
        BIRYANI      = "BIRYANI",      "Biryani"
        PIZZA        = "PIZZA",        "Pizza"
        BURGER       = "BURGER",       "Burgers & Fast Food"
        DESSERTS     = "DESSERTS",     "Desserts & Mithai"
        BEVERAGES    = "BEVERAGES",    "Beverages"
        VEGETARIAN   = "VEGETARIAN",   "Vegetarian"
        VEGAN        = "VEGAN",        "Vegan"
        OTHER        = "OTHER",        "Other"

    id = models.UUIDField(_("RestaurantId"),primary_key=True,default=uuid.uuid4,editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
            verbose_name=('Restaurant Owner'),
            on_delete=models.CASCADE,
            related_name='restaurants',
            limit_choices_to={'role':'RESTAURANT_OWNER'})
    image= models.ImageField(upload_to="restaurants/", null=True, blank=True)
    name = models.CharField(_("Restaurant Name"), max_length=200)
    description = models.TextField(_("Description"),max_length=600)
    cuisine_type = models.CharField(_("Cuisine Type"), max_length=20,choices=CuisineType.choices,default=CuisineType.OTHER)


    #Address fields 
    address = models.CharField(_("Address"), max_length=250)
    city = models.CharField(_("City"), max_length=50)
    pincode = models.CharField(_("Pin Code"), max_length=6, validators=[RegexValidator(r'^\d{6}$', 'Enter a valid 6-digit pin code')])
    phone = models.CharField(_("Phone"), max_length=15, validators=[RegexValidator(r'^\d{10}$', 'Enter a valid 10-digit phone number')])

    lat = models.DecimalField(_("Latitude"), max_digits=9, decimal_places=6,null=True,blank=True)
    long = models.DecimalField(_("longitude"), max_digits=9, decimal_places=6,null=True,blank=True)

    #status flags 
    is_active=models.BooleanField(_('Active Status'),default=True)
    is_open = models.BooleanField(_('Open/Closed'),default=True)
    is_premium = models.BooleanField(_('Premium Restaurant'),default=False,help_text='if true,the restro is  subsidized , zero delivery fee+premium section on app') 
    #delivery configs
    min_order_amount= models.DecimalField(_('Minimum Order Amount'),max_digits=8,decimal_places=2,default=Decimal(50.00))
    avg_preparing_time = models.PositiveIntegerField(_("Preparing Time in minutes"),default=10,help_text='Average Food preparing time in minutes')
    
    average_rating = models.DecimalField(_("Average Rating"), max_digits=3, decimal_places=2,default=Decimal(0.00))
    total_ratings = models.PositiveIntegerField(_('Total Ratings'),default=0)

    #datetime fields 
    created_at = models.DateTimeField(_("Created At"),auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"),auto_now=True)

    class Meta:
        ordering =['-average_rating','-created_at']
        verbose_name_plural = _('Restaurants')
        indexes=[
            models.Index(fields=['name']),
            models.Index(fields=['cuisine_type']),
            models.Index(fields=['city']),
            models.Index(fields=['is_active', 'is_open']),
            models.Index(fields=['is_premium'])
        ]

    def __str__(self):
        return f"{self.name}-{self.city}-{self.cuisine_type}"
    


class Category(models.Model):
    id= models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    restaurant = models.ForeignKey(Restaurants,verbose_name=_("Restaurants"),
                on_delete=models.CASCADE,related_name='categories')
    name = models.CharField(_('Category Name'),max_length=100)
    order = models.PositiveSmallIntegerField(_("Display Order"),default=0) 

    class Meta:
        verbose_name_plural=_('Categories')
        ordering = ['order','name']
        indexes=[models.Index(fields=['restaurant','name'])]
    
    def __str__(self):
        return f"{self.name}-{self.restaurant.name}"


class MenuItem(models.Model):
    id= models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    category = models.ForeignKey(Category,verbose_name=('Category'),on_delete=models.CASCADE,related_name='items')
    name = models.CharField(_("Menu Name"), max_length=100)
    description = models.TextField(_("About menu"),max_length=500,blank=True)
    image = models.ImageField(_('MenuItem Image'),upload_to='menu_items/',blank=True,null=True)

    base_price = models.DecimalField(_('Base Price'),max_digits=8,decimal_places=2,default=Decimal(0.00))

    #flags 
    is_veg =models.BooleanField(_("Vegetarian"),default=False)
    is_bestseller = models.BooleanField(_("BestSeller"),default=False)
    is_available = models.BooleanField(_("Availability"),default=True)

    order = models.PositiveIntegerField(_('Order'),default=0)
    
    #datetime fields 
    created_at = models.DateTimeField(_("Created At"),auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"),auto_now=True)

    class Meta:
        ordering=['order','name']
        verbose_name_plural = _('menuItems')
        indexes=[
            models.Index(fields=['name']),
            ]
    
    def __str__(self):
        return f"{self.name}- ₹{self.base_price}"

    @property
    def has_variants(self):
        return self.variants.exists()  #type:ignore
    
class MenuItemVariants(models.Model):
    id= models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    menu_item = models.ForeignKey(MenuItem,verbose_name=_('Menu Item'),on_delete=models.CASCADE,related_name='variants')
    name = models.CharField(_("Variant Name"), max_length=50,help_text='Half/Full/Small/Regular/Large')
    price = models.DecimalField(_("Variant Price"), max_digits=8, decimal_places=2,default=Decimal(0.00))
    is_available = models.BooleanField(_('Availability'),default=True)

    class Meta:
        unique_together = ('menu_item','name')
        indexes = [models.Index(fields=['menu_item','name'])]
        ordering = ['price']
        verbose_name_plural = _('MenuItemsVariants')

    def __str__(self):
        return f"{self.menu_item.name}-{self.name} ₹{self.price}"





    







