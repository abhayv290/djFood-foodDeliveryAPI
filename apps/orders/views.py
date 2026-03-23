from django.shortcuts import get_object_or_404
from django.utils import timezone
from typing import Type,cast
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsCustomer,IsDeliveryAgent,IsRestaurantOwner
from rest_framework.generics import  CreateAPIView,ListAPIView,RetrieveAPIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from .models import Cart,CartItem,Order,OrderItem,OrderStatusHistory

from .serializers import (
    CartSerializer,CartItemSerializer,OrderSerializer,
    OrderItemSerializer,OrderListSerializer,
    OrderStatusHistorySerializer,OrderStatusUpdateSerializer,
    CheckoutSerializer,
)


@extend_schema(tags=['Carts'])
class CartView(APIView):
    ''' GET - /cart/  get or create
        DELETE- Clear the Cart'''
    permission_classes = [IsAuthenticated,IsCustomer]

    def get_or_create_cart(self,user):
        cart,created = Cart.objects.get_or_create(customer=user)
        return cart
    
    @extend_schema(responses=CartSerializer)
    def get(self,request):
        cart = self.get_or_create_cart(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    #clear the cart
    def delete(self,request):
        cart = self.get_or_create_cart(request.user)
        cart.items.all().delete()  #type:ignore
        cart.restaurant = None
        cart.save(update_fields=['restaurant'])
        return Response({'message':'Cart Cleared'})
    

@extend_schema(tags=['CartItem-Cart'],request=CartItemSerializer,responses=CartSerializer)
class CartItemView(APIView):
    '''
    POST - /cart/item/ - add item to cart
    PATCH - /cart/item/<id> update quantity
    DELETE - /cart/item/<id> remove item from cart '''

    permission_classes = [IsAuthenticated,IsCustomer]
    def get_cart(self,user):
        #helper function 
        cart , _ = Cart.objects.get_or_create(customer=user)
        return cart
    

    def post(self,request):
        cart = self.get_cart(request.user)
        serializer = CartItemSerializer(data=request.data,
                    context = {'request':request,'cart':cart})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response( CartSerializer(cart).data,status=status.HTTP_201_CREATED)

    #quantity update
    def patch(self,request,pk):
        cart = self.get_cart(request.user)
        cart_item = get_object_or_404(CartItem,pk=pk,cart=cart)

        quantity = request.user.get('quantity')
        if quantity is None:
            return Response({
                'error':'quantity is required',

            },status=status.HTTP_400_BAD_REQUEST)
        
        quantity=int(quantity)

        #remove item if quantity set to 0 
        if quantity<=0:
            cart_item.delete()
            #if cart item is empty 
            #reset restaurant  to None ,so that user 
            #can add items from different restaurants

            if not cart.items.exists(): #type:ignore
                cart.restaurant = None 
                cart.save(update_fields=['restaurant'])
            return Response(CartSerializer(cart).data)

        cart_item.quantity = quantity 
        cart_item.save(update_fields=['quantity'])
        return Response(CartSerializer(cart).data)
    
    #delete a cart item
    def delete(self,request,pk):
        cart = self.get_cart(request.user)
        cart_item = get_object_or_404(CartItem,pk=pk,cart=cart)
        cart_item.delete()

        if not cart.items.exists(): #type:ignore
            #reset the Restaurant
            cart.restaurant = None
            cart.save(update_fields=['restaurant'])
            Response(CartSerializer(cart).data)


@extend_schema(tags=['Checkout Flow'], request=CheckoutSerializer, responses=OrderSerializer)
class CheckoutView(APIView):
    '''POST- orders/checkout
    Convert cart to order atomically'''
    
    permission_classes = [IsAuthenticated,IsCustomer]
    
    def post(self,request):
        cart , _ =  Cart.objects.get_or_create(customer = request.user)
        serializer = CheckoutSerializer(data=request.data,
                    context={'cart':cart,'request':request})
        
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response(OrderSerializer(order).data)


@extend_schema(tags=['Orders-Customer'])
class CustomerOrderViewSet(ReadOnlyModelViewSet):
    """
    GET /orders/          -> List of user's orders
    GET /orders/<uuid:pk>/ -> Detailed view of a specific order
    """
    permission_classes = [IsAuthenticated, IsCustomer]
    queryset = Order.objects.all()
    
    def get_queryset(self):
        return super().get_queryset().filter(customer=self.request.user).select_related('restaurant').prefetch_related('items')
    
    def get_serializer_class(self) -> Type:
        if self.action == 'list':
            return OrderListSerializer
        return OrderSerializer


@extend_schema(tags=['Orders-Status Update'],request=OrderStatusUpdateSerializer,responses=OrderStatusHistorySerializer)
class OrderStatusUpdateView(APIView):
    '''PATCH - /orders/<id>/status
    used by restaurant owners and delivery agents to update order status
    each role can only trigger transition they allowed to 
    validated in serializer
    '''
    permission_classes = [IsAuthenticated]

    def get_order(self,pk):
        return get_object_or_404(Order,pk=pk)
    
    def patch(self,request,pk):
        order = self.get_order(pk)

        #role based access 
        # restaurant owner can only update their own order
        if request.user.is_restaurant_owner:
            if order.restaurant.owner != request.user:
                return Response({'error':'You do not own this restaurant'},
                                status=status.HTTP_403_FORBIDDEN)

        #delivery agent can only update their own order
        elif request.user.is_delivery_agent:
            if order.delivery_agent!=request.user:
                return Response({'error':'You are not assigned to this order'},
                                status=status.HTTP_403_FORBIDDEN)

        else:
            return Response({'error':'You don\'t have permission to update this order'},
                            status=status.HTTP_403_FORBIDDEN)
        
        serializer = OrderStatusUpdateSerializer(data=request.data,
                        context={'request':request,'order':order})
        
        serializer.is_valid(raise_exception=True)
        
        data = cast(dict,serializer.validated_data)
        new_status = data['status']
        note = data.get('note')
        #apply status
        order.status = new_status

        #assign a delivery agent when order is accepted by restaurant
        if new_status == order.Status.ACCEPTED and order.delivery_agent is None:
            from .utils import assign_delivery_agent    
            assign_delivery_agent(order)

        #set delivered , when order is delivered
        if new_status == order.Status.DELIVERED:
            order.delivered_at= timezone.now()
            #COD mark as paid on delivery
            if order.payment_method == order.PaymentMethod.COD:
                order.is_paid=True
            order.save(update_fields=['delivered_at','paid','status'])
        
        else:
            order.save(update_fields=['status'])
        
        #Record in History 
        OrderStatusHistory.objects.create(
            order=order,
            status= new_status,
            changed_by = request.user,
            note=note,
        )

        return Response(OrderSerializer(order).data)


@extend_schema(tags=['Orders-Customer'],request=OrderStatusUpdateSerializer,responses=OrderStatusHistorySerializer)
class CustomerCancelOrderView(APIView):
    '''POST - orders/<id>/cancel
    Customer can cancel a order only before restaurant started preparing  the order'''

    permission_classes = [IsAuthenticated,IsCustomer]

    def post(self,request,pk):
        order = get_object_or_404(Order,pk=pk,customer=request.user)

        #cannot cancel before order place 
        if order.status!=Order.Status.PLACED:
            return Response({
                'error':'Order cannot be cancelled at this stage'
            },status=status.HTTP_400_BAD_REQUEST)
        
        reason  = request.data.get('reason','')
        order.status = Order.Status.CANCELLED
        order.cancelled_by = Order.CancelledBy.CUSTOMER
        order.cancellation_reason= reason
        order.save(update_fields=['status','cancelled_by','cancellation_reason'])

        #notify the agent if assigned so that he can update his status to available
        #not triggering direct to available cz , agent could be handling two orders 
        
        if order.delivery_agent:
            from .utils import notify_agent
            notify_agent(order.delivery_agent,order)
        #Update the orderStatus History
        OrderStatusHistory.objects.create(
            order = order ,
            status= Order.Status.CANCELLED,
            changed_by = request.user,
            note  = f"Cancelled by customer {reason}".strip(),
        )
        return Response({
            'message':'Order Cancelled.',
            'order_id' : str(order.id),
        },status=status.HTTP_200_OK)


@extend_schema(tags=['Orders-Restaurants'])
class RestaurantOrderViewSet(ReadOnlyModelViewSet):
    '''GET orders/restaurants/<restaurant_id>
    List all the orders belongs to the restaurant to dashboard
    GET orders/restaurants/<restaurant_id>/<order_id> 
    Retrieve : Detailed Order View
    '''
    permission_classes =[IsAuthenticated,IsRestaurantOwner]
    queryset = Order.objects.all()
    filterset_fields = {
        'status' : ['exact']
    }
    def get_serializer_class(self)->Type:
        if self.action=='list':
            return OrderListSerializer
        return OrderSerializer

    def get_queryset(self):
        restaurant = get_object_or_404(self.request.user.restaurants) #type:ignore
        return super().get_queryset().filter(
            restaurant=restaurant
        ).select_related('customer').prefetch_related('items')

    


@extend_schema(tags=['Orders-Agents'])
class AgentOrderViewSet(ReadOnlyModelViewSet):
    '''
    Viewset for Agents to view their assigned orders.
     LIST: orders/agents/
     RETRIEVE: orders/agents/<id>/
    '''
    permission_classes = [IsAuthenticated, IsDeliveryAgent]
    queryset = Order.objects.all()
    def get_serializer_class(self)->Type:
        if self.action == 'list':
            return OrderListSerializer
        return OrderSerializer

    def get_queryset(self):
        return super().get_queryset().filter(delivery_agent=self.request.user).select_related('customer').prefetch_related('items')




    





       
        

        







