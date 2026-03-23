from decimal import Decimal 
from django.db import models
DELIVERY_FEE =  Decimal(20.00)
FREE_DELIVERY_DISTANCE_KM = 1 
DELIVERY_RATE_PER_KM = Decimal(10.00)

def calculate_delivery_fee(restaurant,distance_km=None):
    """
    Currently going with flat fee 
    TODO: gonna add the distance based calculation

    Rules: 
    premium       -> ₹0  (platform subsidized)
    withing 1 km  -> ₹0
    beyond  1 km  -> ₹20 (standard) + distance(in km)*₹10
    """

    if restaurant.is_premium:
        return Decimal(0.00)
    
    if distance_km is None:
        return DELIVERY_FEE
    
    if distance_km<=FREE_DELIVERY_DISTANCE_KM:
        return Decimal(0.00)
    
    #TODO (distance_km-1)* delivery_rate_per_km
    return DELIVERY_FEE



def assign_delivery_agent(order):
    '''
    Helper function to assign delivery agent to an order when restaurant accepts it.
    Currently we are assigning only the first available agent ,with most time spend idle.
    TODO: Later when we integrate postgis then we'll add real time distance calculation and assign the nearest agent with  most time spend idle.
    '''
    from apps.users.models import DeliveryAgentProfile
    from .models import Order
    agent_profile = DeliveryAgentProfile.objects.filter(
        status=DeliveryAgentProfile.AgentStatus.AVAILABLE,
          is_verified=True,user__is_active=True
    ).order_by('last_location_update').first()

    if not agent_profile:
        print(f"[ASSIGN] No Agent Available at the moment ,Please try again after some time, or use the restaurant dashboard to assign an agent manually")
        return None 
    
    order.delivery_agent = agent_profile.user
    order.save(update_fields=['delivery_agent'])

    agent_profile.status = DeliveryAgentProfile.AgentStatus.ON_DELIVERY
    agent_profile.save(update_fields=['status'])

    notify_agent(agent_profile,order)


def notify_agent(agent,order):
    '''
    helper function to send a notification to the assigned agent about the new delivery assignment
    currently using long ,gonna add a notification service later
    '''
    print(f"[NOTIFY] Agent {agent.user.email} assigned to Order-{order.id} for delivery")