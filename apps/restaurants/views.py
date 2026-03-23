from typing import Type
from rest_framework.filters import OrderingFilter,SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from core.permissions import IsRestaurantOwner,IsOwnerOfRestaurant

from .filters import RestaurantFilter,MenuItemFilter
from .models import Restaurants,Category,MenuItem,MenuItemVariants
from .serializers import (
    RestaurantDetailSerializer,RestaurantListSerializer,
    RestaurantWriteSerializer,CategorySerializer,MenuItemListSerializer,
    MenuItemWriteSerializer,MenuItemVariantSerializer
)



@extend_schema(tags=['Restaurants'])
class RestaurantViewSets(ModelViewSet):
    queryset = Restaurants.objects.all()

    # filters / search / ordering 
    filter_backends = [DjangoFilterBackend,SearchFilter,OrderingFilter]
    filterset_class=RestaurantFilter
    search_fields = ['name','city','cuisine_type','description',]

    ordering_fields = ['average_rating','total_ratings','avg_preparing_time','created_at']

    def get_serializer_class(self) -> Type:
        if self.action == 'list':
            return RestaurantListSerializer
        if self.action == 'retrieve':
            return RestaurantDetailSerializer
        return RestaurantWriteSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'my_restaurants':
            return [IsAuthenticated(), IsRestaurantOwner()]  
        return [IsAuthenticated(), IsRestaurantOwner()]

    def get_queryset(self):  # type: ignore
        user = self.request.user
        if user.is_authenticated and user.is_restaurant_owner:  # type: ignore
            if self.action == 'my_restaurants':
                return Restaurants.objects.filter(owner=user)
        return Restaurants.objects.filter(is_active=True)

    def perform_update(self, serializer):
        self.check_object_permissions(self.request, self.get_object())
        serializer.save()

    def perform_destroy(self, instance):
        self.check_object_permissions(self.request, instance)
        instance.delete()

    @action(detail=False, methods=['GET'], url_path='mine') 
    def my_restaurants(self, request):
        restaurants = Restaurants.objects.filter(owner=request.user)
        serializer  = RestaurantListSerializer(restaurants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['PATCH'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        restaurant = self.get_object()
        self.check_object_permissions(request, restaurant)
        restaurant.is_open = not restaurant.is_open
        restaurant.save(update_fields=['is_open'])
        return Response({
            'is_open': restaurant.is_open,
            'message': f"Restaurant is now {'Open' if restaurant.is_open else 'Closed'}"
        })



@extend_schema(tags=['Categories-Restaurants'])
class CategoryViewSets(ModelViewSet):
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['list','retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(),IsRestaurantOwner()]
    
    def get_restaurant(self):
        return get_object_or_404(Restaurants,pk=self.kwargs['restaurant_pk'],is_active=True)
    
    
    def get_queryset(self): #type:ignore
        return Category.objects.filter(
            restaurant=self.get_restaurant()
        ).prefetch_related('items','items__variants')
    
    def get_serializer_context(self):
        #passing the data to serializers ( restaurants )
        context = super().get_serializer_context()
        context['restaurants'] = self.get_restaurant()
        return context
    

    def perform_create(self,serializer):
        rest = self.get_restaurant()
        #verify ownership
        if rest.owner !=self.request.user:
            raise PermissionDenied('You do not own this restaurant')
        
        if rest.categories.count() >= 20: #type:ignore
            raise PermissionDenied('Max 20 category allowed per restaurant')
        serializer.save(restaurant=rest)
    

    def perform_update(self, serializer):
        rest = self.get_restaurant()
        if rest.owner !=self.request.user:
            raise PermissionDenied('You do not own this restaurant')

        serializer.save()
    
    def perform_destroy(self, instance):
        if instance.restaurant.owner!=self.request.user:
            raise PermissionDenied('You do not own this restaurant')
        instance.delete()


@extend_schema(tags=['Menu-Restaurants'])
class MenuItemViewSets(ModelViewSet):
    queryset = MenuItem.objects.all()
    filter_backends=[DjangoFilterBackend,OrderingFilter,SearchFilter]
    filterset_class = MenuItemFilter
    
    search_fields = ['name','description','category__name',]
    ordering_fields = ['order','name','base_price']
    ordering=['order']
    def get_permissions(self):
        if self.action in ['list','retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(),IsRestaurantOwner()]
    
    def get_serializer_class(self)->Type:
        if self.action in ['list','retrieve'] :
            return MenuItemListSerializer
        return MenuItemWriteSerializer

    def get_restaurants(self):
        #helper function 
        return get_object_or_404(Restaurants,pk=self.kwargs['restaurant_pk'],is_active=True)
    

    def get_queryset(self):
        return super().get_queryset().filter(
            category__restaurant = self.get_restaurants()
        ).select_related('category').prefetch_related('variants')
       
    

    def perform_create(self,serializer):
        rest = self.get_restaurants()

        if rest.owner != self.request.user:
            raise PermissionDenied('You do not this restaurant')
        
        #verify the category belong to this one
        category = serializer.validated_data.get('category')
        if category and category.restaurant!=rest:
            raise PermissionDenied('Category do not belong this one')
        
        serializer.save()

    def perform_update(self,serializer):
        rest = self.get_restaurants()

        if rest.owner != self.request.user:
            raise PermissionDenied('You do not this restaurant')
        
        serializer.save()

    def perform_destroy(self,instance):
        if instance.category.restaurant.owner != self.request.user:
            raise PermissionDenied('You do not this restaurant')
        instance.delete()
    
    #Custom Action PATCH /restaurants/<id>/menu-items/<id>/toggle/
    @action(detail=True,methods=['PATCH'],url_path='toggle')
    def toggle_availability(self,request,pk=None,restaurant_pk=None):
        '''Quick Toggle for item availability'''
        item = self.get_object()
        if item.category.restaurant.owner!=request.user:
            PermissionDenied('you do not own this restaurant')
        item.is_available = not item.is_available
        item.save(update_fields=['is_available'])
        return Response({
            'is_available':item.is_available,
            'message':f"{item.name} is now {'available' if item.is_available else 'unavailable' }."
        })

@extend_schema(tags=['Variants-Menu'])
class MenuItemVariantViewSets(ModelViewSet):
    serializer_class=MenuItemVariantSerializer

    def get_permissions(self):
        if self.action in ['list','retrieve'] :
            return [AllowAny()]
        return [IsAuthenticated(),IsRestaurantOwner()]
    
    def get_menu_item(self):
        #helper function 
        return get_object_or_404(
            MenuItem,pk=self.kwargs['menu_item_pk'],
            category__restaurant__pk=self.kwargs['restaurant_pk']
        )
     
    def get_queryset(self): #type:ignore
        return MenuItemVariants.objects.filter(menu_item=self.get_menu_item())
    

    def perform_create(self, serializer):
        menu_item  = self.get_menu_item()
        restaurant = menu_item.category.restaurant
        if restaurant.owner != self.request.user:
            raise PermissionDenied("You do not own this restaurant.")
        serializer.save(menu_item=menu_item)
 
    def perform_update(self, serializer):
        restaurant = self.get_object().menu_item.category.restaurant
        if restaurant.owner != self.request.user:
            raise PermissionDenied("You do not own this restaurant.")
        serializer.save()
 
    def perform_destroy(self, instance):
        restaurant = instance.menu_item.category.restaurant
        if restaurant.owner != self.request.user:
            raise PermissionDenied("You do not own this restaurant.")
        instance.delete()
    

    

    




    