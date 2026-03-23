from rest_framework.permissions import BasePermission


#Creating custom Permission classes to handle the permission for all role type 

class IsCustomer(BasePermission):
    message='Access restricted to customers.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_customer


class IsRestaurantOwner(BasePermission):
    message = 'Access restricted to restaurant owners.'
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_restaurant_owner

class IsOwnerOfRestaurant(BasePermission):
    message = 'you dont own this restaurant'
    def has_object_permission(self, request, view, obj):
        return request.user == obj.owner

class IsDeliveryAgent(BasePermission):
    message  = 'Access restricted to delivery agents'
    def has_permission(self,request,view):
        return request.user and request.user.is_authenticated and request.user.is_delivery_agent
    


