from rest_framework.serializers import Serializer,ModelSerializer,ValidationError
from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from apps.restaurants.models import MenuItem,MenuItemVariants
from apps.users.models import CustomerAddress
from .models import Cart,CartItem , Order,OrderItem,OrderStatusHistory
from .utils import calculate_delivery_fee
from decimal import Decimal



class CartItemSerializer(ModelSerializer):
    #read only fields 
    item_name = serializers.CharField(source='menu_item.name',read_only=True)
    variant_name=serializers.CharField(source='variant.name',read_only=True)
    unit_price = serializers.DecimalField(max_digits=8 ,decimal_places=2,read_only=True)
    subtotal = serializers.DecimalField(max_digits=8 ,decimal_places=2,read_only=True)

    #write fields 
    menu_item = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all())
    variant = serializers.PrimaryKeyRelatedField(queryset=MenuItemVariants.objects.all(),
                                                 required=False,allow_null=True)
    
    class Meta:
        model = CartItem
        fields = ('id','menu_item','item_name','variant','variant_name',
                  'quantity','unit_price','subtotal')
        
        read_only_fields = ('id',)
    
    def validate(self,attrs):
        menu_item = attrs['menu_item']
        variant= attrs['variant']
        cart = self.context['cart']
    
        #item availability check 
        if not menu_item.is_available:
            raise ValidationError(f"{menu_item.name} is currently unavailable")
                
        #check if the variant is belong to the item 
        if variant and variant.menu_item!=menu_item:
            raise ValidationError(f"{variant.name} does not belong to this menu")

        #variant availability 
        if variant and not variant.is_available:
            raise ValidationError(f"{variant.name} is currently unavailable")

        

        #Restaurant conflict in cart 
        #only one restaurant allowed in one cart 
        item_restaurant = menu_item.category.restaurant
        if cart.restaurant and cart.restaurant!=item_restaurant:
            raise ValidationError({
                'conflict':True,
                'message' : 'Your cart have items from different restaurant',
                'current_restaurant' : str(cart.restaurant.id),
                'new_restaurant' : str(item_restaurant.id)
            })
        
        return attrs
    

    def create(self,validated_data):
        cart = self.context['cart']
        menu_item = validated_data['menu_item']
        variant=validated_data['variant']
        quantity = validated_data['quantity']

        #Upsert Pattern 
        #Crete a Cart item if does not exists
        #if exists increment the quantity of that item
        cart_item,created  = CartItem.objects.get_or_create(
            cart=cart,menu_item=menu_item,variant=variant,quantity=quantity
        )
        if not created:
            cart_item.quantity+=quantity
            cart_item.save(update_fields=['quantity'])
        
        if not cart.restaurant:
            cart.restaurant=menu_item.category.restaurant
            cart.save(update_fields=['restaurant']) 
        
        return cart_item


        
class CartSerializer(ModelSerializer):
    items = CartItemSerializer(many=True,read_only=True)
    subtotal = serializers.DecimalField(max_digits=8 , decimal_places=2,read_only=True)
    delivery_fee = serializers.SerializerMethodField()
    total_amount = serializers.DecimalField(max_digits=8 , decimal_places=2,read_only=True)
    item_count=serializers.IntegerField(read_only=True)
    is_premium = serializers.BooleanField(source='restaurant.is_premium',read_only=True)
    is_below_minimum = serializers.SerializerMethodField()
    min_order_amount = serializers.DecimalField(max_digits=5,decimal_places=2,source='restaurant.min_order_amount',read_only=True)
    restaurant_name =serializers.CharField(source = 'restaurant.name',read_only=True)


    class Meta:
        model= Cart
        fields = ('id','restaurant_name','subtotal','total_amount','item_count','is_premium','is_below_minimum','delivery_fee', 'min_order_amount' ,  'items')
        read_only_fields=('id',)


    def get_delivery_fee(self,obj):
        if not obj.restaurant:
            return '0.00'
        return calculate_delivery_fee(obj.restaurant)
    
    def get_total_amount(self,obj):
        return obj.subtotal + Decimal(str(self.get_delivery_fee(obj)))
    
    def get_is_below_minimum(self,obj):
        if not obj.restaurant:
            return False
        elif obj.subtotal<obj.restaurant.min_order_amount:
            return True
        else:
            return False



    



#convert cart to order (cart items to order items atomically)
class CheckoutSerializer(Serializer):
    payment_method= serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    selected_address = serializers.PrimaryKeyRelatedField(queryset=CustomerAddress.objects.all(),required=False,allow_null=True)

    def validate(self,attrs):
        cart =self.context['cart']
        customer = self.context['request'].user
        #cart empty 
        if not cart.items.exists():
            raise ValidationError('Your cart is Empty')
        
        #restaurant Open
        if not (cart.restaurant.is_active or cart.restaurant.is_open):
            raise ValidationError(f"{cart.restaurant.name} is currently closed")
        
        # revalidate the menuitems and variants if its available
        unavailable = []
        for item in cart.items.select_related('menu_item','variant'):
            if not item.menu_item.is_available:
                unavailable.append(item.menu_item.name)
            if item.variant and  not item.variant.is_available:
                unavailable.append(f"{item.menu_item.name}-{item.variant.name}")
        
        if len(unavailable):
            raise ValidationError(
                f"Some Items are no longer available ${','.join(unavailable)}"
            )

        #enforce minimum order amount
        if cart.subtotal<cart.restaurant.min_order_amount:
            raise ValidationError(f"Minimum order amount is ₹{cart.restaurant.min_order_amount} ."
                                  f"You cart total is ₹{cart.subtotal}")
        

        #use selected address if provided, else fallback to default/first saved address
        selected_address = attrs.get('selected_address',None)
        if selected_address and selected_address.customer != customer.customer_profile:
            raise ValidationError({'selected_address':'Invalid address selection'})

        if not selected_address:
            selected_address = customer.customer_profile.addresses.filter(is_default=True).first() or customer.customer_profile.addresses.first()

        if not selected_address:
            raise ValidationError('Please add a delivery address before checkout')
        
        attrs['cart']=cart
        attrs['restaurant']=cart.restaurant
        attrs['selected_address']=selected_address
        return attrs


    def get_delivery_address(self, address):
        if address:
            return f"{address.flat_number}, {address.address_line}, {address.pincode}, phone: {address.receiver_phone}, map: {address.formatted_address}"
        return None

    def get_delivery_lat(self, address):
        return address.lat if address else None

    def get_delivery_long(self, address):
        return address.long if address else None

    #creating checkout atomically(handles midway failure)
    @transaction.atomic
    def create(self,validated_data):
        cart =validated_data.pop('cart')
        restaurant=validated_data.pop('restaurant')
        selected_address = validated_data.pop('selected_address',None)
        customer = self.context['request'].user

        delivery_address = self.get_delivery_address(selected_address)
        delivery_lat = self.get_delivery_lat(selected_address)
        delivery_long = self.get_delivery_long(selected_address)
        delivery_fee = Decimal(str(calculate_delivery_fee(restaurant)))
        total_amount = cart.subtotal + delivery_fee

        #creating the order 
        order = Order.objects.create(
            customer = customer,restaurant=restaurant,
            payment_method = validated_data['payment_method'],
            delivery_address = delivery_address,
            delivery_lat = delivery_lat,
            delivery_long = delivery_long,
            subtotal = cart.subtotal,
            delivery_fee = delivery_fee,
            total_amount = total_amount,
            is_paid=False #for cod orders
        )

        #copying each cart item into order item 
        for item in cart.items.select_related('menu_item','variant'):
            OrderItem.objects.create(
                order = order ,
                menu_item  = item.menu_item,
                variant = item.variant,
                quantity= item.quantity,
                item_name = item.menu_item.name,
                variant_name = item.variant.name if item.variant else '',
                price = item.unit_price,
            ) 

        #Recording initial state for orderStatusHistory
        OrderStatusHistory.objects.create(
            order = order ,
            status = Order.Status.PLACED,
            changed_by = customer,
            note=  'Order Placed by Customer'
        )

        #clear the cart 
        cart.items.all().delete()
        cart.restaurant = None
        cart.save(update_fields=['restaurant'])

        return order 

     
'''
Order Serializer

'''

class OrderItemSerializer(ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=8,decimal_places=2,read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id','item_name','variant_name','quantity','price','subtotal')


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.name',read_only=True) 

    class Meta:
        model = OrderStatusHistory
        fields = ('status','changed_by_name','changed_at','note')


class OrderSerializer(ModelSerializer):
    #read only order details 
    items = OrderItemSerializer(many=True,read_only=True)
    status_history = OrderStatusHistorySerializer(many=True,read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name',read_only=True)
    customer_name = serializers.CharField(source='customer.name',read_only=True)

    class Meta:
        model = Order
        fields = ('id','customer_name','restaurant_name','status','payment_method',
                  'is_paid','subtotal' , 'delivery_fee','total_amount',
                  'placed_at','delivery_address' ,'delivery_agent','delivered_at','items','status_history')


class OrderListSerializer(ModelSerializer):
    #used in order history 
    restaurant_name = serializers.CharField(source='restaurant.name',read_only=True)
    restaurant_image = serializers.ImageField(source='restaurant.image',read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id','restaurant_name','restaurant_image','status', 'total_amount',
                  'payment_method','is_paid','placed_at','item_count')

    def get_item_count(self,obj):
        return obj.items.count()



class OrderStatusUpdateSerializer(Serializer):
    '''Used by restaurant owners and delivery agents to update 
    the status of the order
    validates the state machine '''

    status = serializers.ChoiceField(choices=Order.Status.choices)
    note = serializers.CharField(required=False,allow_null=True)

    def validate_status(self,value):
        order = self.context['order']

        #state machine validates 
        #can_transition_to is defined on the order model 

        if not order.can_transition_to(value):
            raise ValidationError(f"Cannot transition from {order.status} to {value}."
                                  f"Valid next status:{order.VALID_STATUS_TRANSITIONS.get(order.status,[])}")
        return value
    

    def validate(self,attrs):
        order = self.context['order']
        user = self.context['request'].user
        new_status = attrs['status']

        #who can trigger which transition 
        restaurant_transition = [
            Order.Status.ACCEPTED,
            Order.Status.PREPARING,
            Order.Status.READY,
            Order.Status.CANCELLED
        ]
        agent_transition = [
            Order.Status.PICKED_UP,
            Order.Status.DELIVERED
        ]
        

        if new_status in restaurant_transition and not user.is_restaurant_owner:
            raise ValidationError('Only Restaurant Owner perform this action')
        
        if new_status in agent_transition and not user.is_is_delivery_agent:
            raise ValidationError('Only Delivery agents can perform this action')
        
        if new_status == Order.Status.CANCELLED:
            #customer can only cancel before restaurant accepts
            if user.is_customer and order.status!=Order.Status.PLACED:
                raise ValidationError(
                    'Order can only be canceled before it accepted'
                )
            
        return attrs 





    


