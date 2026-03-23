import uuid
from django.db import models
from django.conf import settings 
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from apps.restaurants.models import Restaurants,MenuItem,MenuItemVariants
from apps.users.models import UserRole



class Cart(models.Model):
    id = models.UUIDField(_("cartId"),primary_key=True,default=uuid.uuid4,editable=False)
    customer = models.OneToOneField(settings.AUTH_USER_MODEL,verbose_name=_('Customer'),on_delete=models.CASCADE,related_name='cart',limit_choices_to={'role':UserRole.CUSTOMER})

    restaurant = models.ForeignKey(Restaurants,verbose_name=_('Restaurants'),on_delete=models.SET_NULL,related_name='cart',null=True,blank=True)

    created_at = models.DateTimeField(_('CreatedAt'),auto_now_add=True)
    updated_at = models.DateTimeField(_('UpdatedAt'),auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Cart-{self.customer.email}"
    
    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all()) #type:ignore
    
    @property
    def item_count(self):
        return self.items.count() #type:ignore


class CartItem(models.Model):
    id = models.UUIDField(_("Id"),primary_key=True,default=uuid.uuid4,editable=False)
    cart = models.ForeignKey(Cart,verbose_name=_('Cart'),on_delete=models.CASCADE,related_name='items')
    menu_item= models.ForeignKey(MenuItem,verbose_name=_('Menu Item'),on_delete=models.CASCADE)
    variant = models.ForeignKey(MenuItemVariants,verbose_name=_('Menu Item Variant'),on_delete=models.SET_NULL,null=True,blank=True)
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ['cart','menu_item','variant']
    
    def __str__(self):
        return f"{self.menu_item.name}-{self.variant.name if self.variant else ''}-{self.quantity}"
    
    @property
    def unit_price(self):
        return self.variant.price  if self.variant else self.menu_item.base_price
    
    @property
    def subtotal(self):
        return self.unit_price*self.quantity
    

class Order(models.Model):
    class Status(models.TextChoices):
        PLACED     = "PLACED",     "Placed"
        ACCEPTED   = "ACCEPTED",   "Accepted"
        PREPARING  = "PREPARING",  "Preparing"
        READY      = "READY",      "Ready for Pickup"
        PICKED_UP  = "PICKED_UP",  "Picked Up"
        DELIVERED  = "DELIVERED",  "Delivered"
        CANCELLED  = "CANCELLED",  "Cancelled"

    class PaymentMethod(models.TextChoices):
        COD = 'COD' , 'Cash On Delivery'
        UPI =  'UPI' , 'UPI Payment Gateway'
        CARD = 'CARD' , 'Credit/Debit Card'
        NETBANKING = 'NETBANKING' , 'Net Banking' 
    
    
    class CancelledBy(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        RESTAURANT = 'RESTAURANT', 'Restaurant' 
        SYSTEM = 'SYSTEM', 'System'
    

    id = models.UUIDField(_("orderId"),primary_key=True,default=uuid.uuid4,editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name=_('Customer'),on_delete=models.PROTECT,related_name='orders',limit_choices_to={'role':UserRole.CUSTOMER})
    restaurant = models.ForeignKey(Restaurants,verbose_name=_('Restaurant'),on_delete=models.PROTECT,related_name='orders')
    delivery_agent = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name=_('Delivery Agent'),on_delete=models.SET_NULL,null=True,blank=True,related_name='deliveries',limit_choices_to={'role':UserRole.DELIVERY_AGENT})
    #Status - state machine
    status = models.CharField(_('Status'),max_length=20,choices=Status.choices,default=Status.PLACED,db_index=True)
    delivery_address = models.TextField() #  snapshot of customer address at the time of order placement
    delivery_lat = models.DecimalField(_('Delivery Latitude'), max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_long = models.DecimalField(_('Delivery Longitude'), max_digits=9, decimal_places=6, null=True, blank=True)

    #payment details 
    payment_method = models.CharField(_('Payment Method'), max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    
    is_paid = models.BooleanField(_('Paid'),default=False)

    #pricing snapshot - capture total amount at the time of order placement to avoid issues with later menu price changes
    subtotal = models.DecimalField(_('Total Amount'), max_digits=8, decimal_places=2, default=Decimal(0.00))
    delivery_fee = models.DecimalField(_('Delivery Fee'), max_digits=5, decimal_places=2, default=Decimal(0.00))
    total_amount = models.DecimalField(_('Total Amount'), max_digits=8, decimal_places=2, default=Decimal(0.00))

    cancelled_by = models.CharField(_('Cancelled By'), max_length=20, choices=CancelledBy.choices, null=True, blank=True)
    cancellation_reason = models.TextField(_('Cancellation Reason'),blank=True,null=True)

    #timing fields
    placed_at = models.DateTimeField(_('Placed At'), auto_now_add=True)
    delivered_at = models.DateTimeField(_('Delivered At'), null=True, blank=True)


    class Meta:
        ordering = ['-placed_at']

    def __str__(self):
        return f"Order-{self.id} by {self.customer.email} from {self.restaurant.name}"   
    
    
    #State Machine valid transition of order status
    #each status maps what are the valid next states
    VALID_STATUS_TRANSITIONS = {
        Status.PLACED: [Status.ACCEPTED, Status.CANCELLED],
        Status.ACCEPTED: [Status.PREPARING, Status.CANCELLED],
        Status.PREPARING: [Status.READY, Status.CANCELLED],
        Status.READY: [Status.PICKED_UP, Status.CANCELLED],
        Status.PICKED_UP: [Status.DELIVERED, Status.CANCELLED],
        Status.DELIVERED: [], #terminal state
        Status.CANCELLED: [], #terminal state
    }

    
    def can_transition_to(self,new_status):
        """Check if transition is valid before saving """
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.Status(self.status),[])


class OrderItem(models.Model):
    id = models.UUIDField(_("Id"),primary_key=True,default=uuid.uuid4,editable=False)
    order = models.ForeignKey(Order,verbose_name=_('Order'),on_delete=models.CASCADE,related_name='items')
    menu_item = models.ForeignKey(MenuItem,verbose_name=_('Menu Item'),on_delete=models.PROTECT)
    variant = models.ForeignKey(MenuItemVariants,verbose_name=_('Menu Item Variant'),on_delete=models.SET_NULL,null=True,blank=True)
    quantity = models.PositiveSmallIntegerField(default=1)
    
    #Snapshot of item name and price at the order place time
    item_name = models.CharField(_('Item Name'), max_length=250)
    variant_name = models.CharField(_('Variant Name'), max_length=100, blank=True)
    price = models.DecimalField(_('Price at Order Time'), max_digits=8, decimal_places=2, default=Decimal(0.00))

    class Meta:
        unique_together = ['order','menu_item','variant']
    
    def __str__(self):
        return f"{self.item_name}-{self.variant_name if self.variant_name else ''}-{self.quantity}"
    
    @property
    def subtotal(self):
        return self.price*self.quantity
    

class OrderStatusHistory(models.Model):
    '''Model to track the history of status changes for each order
    Useful for giving customers a timeline of their order and for analytics on average time spent in each status'''
    id = models.UUIDField(_("Id"),primary_key=True,default=uuid.uuid4,editable=False)
    order = models.ForeignKey(Order,verbose_name=_('Order'),on_delete=models.CASCADE,related_name='status_history')
    status = models.CharField(_('Status'),max_length=20,choices=Order.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name=_('Changed By'),on_delete=models.SET_NULL,null=True,blank=True)
    changed_at = models.DateTimeField(_('Changed At'), auto_now_add=True)
    note = models.TextField(_('Note'), blank=True,null=True)

    class Meta:
        ordering = ['-changed_at']
        db_table = 'order_status_history'
        verbose_name_plural = 'Order Status Histories'
    
    def __str__(self):
        return f"Order {self.order.id} changed to {self.status} at {self.changed_at}"





   








    




