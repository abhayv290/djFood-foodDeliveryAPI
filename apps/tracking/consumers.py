import json 
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError


class OrderTrackingConsumer(AsyncJsonWebsocketConsumer):
    '''
    WebSocket consumer for real time order tracking 
    URL ws://localhost:8000/ws/tracking/<order_id>/?token=<access_token>

    Connection Lifecycle 
    connect() -> client open websocket 
    disconnect => client closes websocket or connection drops 
    receive -> client send a message (rare for tracking)

    '''
    
    async def connect(self):
        url_route = self.scope.get("url_route", {})
        self.order_id   = url_route.get("kwargs", {}).get("order_id")
        self.group_name = f"order_{self.order_id}"

        #Authenticate via jwt from query params 
        #websocket cannot sends auth headers like http
        #jwt is passed via query params ?token=<access_token>
        user = await self.get_user_from_token()

        if user is None:
            #reject unauthorized access
            await self.close(code=4001)
            return 

        #only relevant parties can track the order
        has_access = await self.check_order_access(user,self.order_id)
        if not has_access:
            await self.close(code=4003)
            return 
        
        #join the order's channels group
        await self.channel_layer.group_add(
            self.group_name,self.channel_name
        )

        await self.accept()

        #send initial channel confirmation 
        await self.send(text_data=json.dumps({
            'type':'connection Established',
            'order_id' :self.order_id,
            'message':'Connected to Order Tracking'
        }))


    async def disconnect(self, code:int) -> None:
        #leave the group on disconnect
        #group-discard unsubscribe - no more broadcast to this consumer
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None, **kwargs):
        #tracking is server =>client only
        #client dont send messages in this case
        #receive is more completeness ping/pong handling if needed
        pass


    async def location_update(self,event):
        #Receive broadcast from channel layer  , forward to websocket client 
       await self.send(text_data=json.dumps({
           'type':'location_update',
           'latitude' :event['latitude'],
           'longitude' : event['longitude'],
           'status' : event['status'],
           'timestamp' : event['timestamp']  
       }))

    async def order_status_update(self,event):
        #Receive Order status change broadcast , forwards to client 
        await self.send(text_data=json.dumps({
            'type':'order_status_update',
            'status' :event['status'],
            'message' :event['message'],
        }))

    #helper functions
    async def get_user_from_token(self):
        #Extract and    validate the token from ws query param 

        try:
            qs = self.scope.get('query_string',b'').decode()
            params = dict(
                param.split('=') for param in qs.split('&') if '=' in param
            )
            token_str = params.get('token')
            if not token_str:
                return None
            
            #validate JWT 
            token = AccessToken(token_str) #type:ignore
            user_id = token.get('user_id')
            user = await self.get_user(user_id) 
            return user
            
        except (TokenError,KeyError,Exception):
            return None    

    @database_sync_to_async   
    def get_user(self,user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(id=user_id,is_active=True)
        except User.DoesNotExist:
            return None
        
    @database_sync_to_async
    def check_order_access(self,user,order_id):
        #only these people can track the order
        # 1- the customer who placed it 
        # 2 - the restaurant owner ,where the order placed
        # 3 - the assigned delivery agent 
        from apps.orders.models import Order
        try:
            order = Order.objects.select_related(
                'customer','delivery_agent','restaurant__owner'
            ).get(pk=order_id)
            return (
                order.customer==user or order.delivery_agent == user or order.restaurant.owner==user
            )
        except Order.DoesNotExist:
            return False
