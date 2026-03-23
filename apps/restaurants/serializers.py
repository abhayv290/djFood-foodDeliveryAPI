from rest_framework import serializers
from rest_framework.serializers import ModelSerializer ,ValidationError
from .models import Restaurants,Category,MenuItem,MenuItemVariants



class MenuItemVariantSerializer(ModelSerializer):
    class Meta:
        model = MenuItemVariants
        fields= ('id','name','price','is_available')
        read_only_fields =('id',)


#for Listing in nesting with their categories
class MenuItemListSerializer(ModelSerializer):
    variants = MenuItemVariantSerializer(many=True,read_only=True)
    effective_price = serializers.SerializerMethodField() #for displaying staring from X

    class Meta:
        model = MenuItem
        fields = ('id','name','description','image','base_price','effective_price',
                  'is_veg','is_bestseller','is_available','has_variants','variants')
        

    def get_effective_price(self,obj):
        if obj.has_variants:
            #cheapest available variants
            cheapest = obj.variants.filter(is_available=True).first()
            return cheapest.price if cheapest else obj.base_price
        return obj.base_price
    




#for menu item write serializer (use by restaurant owners)
class MenuItemWriteSerializer(ModelSerializer):
    class Meta:
        model  = MenuItem
        fields = (
            "id", "name", "description", "image",
            "base_price", "is_veg", "is_bestseller",
            "is_available", "order",'category'
        )
        read_only_fields = ('id',)
    
    def validate_base_price(self,value):
        if value<=0:
            raise ValidationError('Price must be greater than 0')
        return value
    


class CategorySerializer(ModelSerializer):
    items = MenuItemListSerializer(many=True,read_only=True)
    
    class Meta:
        model=Category
        fields = ('id','name','order','items')
        read_only_fields=('id',)


    def validate_name(self,value):
        request = self.context.get('request')
        restaurant = self.context.get('restaurant')

        if restaurant:
            qs = Category.objects.filter(restaurant=restaurant,name=value)

            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"Category {value} already exists in this restaurant")

        return value
    


 
class RestaurantListSerializer(ModelSerializer):
    class Meta:
        model  = Restaurants
        fields = (
            "id", "name", "cuisine_type", "image",
            "average_rating", "total_ratings",
            "avg_preparing_time",
            "min_order_amount", "is_open", "city",'is_premium'
        )


#Nested restaurant data with entire category and menu items
class RestaurantDetailSerializer(ModelSerializer):
    categories = CategorySerializer(many=True,read_only=True)
    owner_name = serializers.CharField(source='owner.name',read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model  = Restaurants
        fields = (
            "id", "name", "description", "cuisine_type", "image",
            "address", "city", "pincode","phone",
            "average_rating","total_ratings", "total_items",
            "avg_preparing_time", "min_order_amount", 'is_premium',
            "is_open", "owner_name",
            "categories",   # full nested menu at the bottom
        )

    def get_total_items(self,obj):
        return MenuItem.objects.filter(category__restaurant=obj,is_available=True).count()
    


class RestaurantWriteSerializer(ModelSerializer):
    class Meta:
        model = Restaurants
        fields = (
            "name", "description", "cuisine_type", "image",
            "address","city", "pincode","phone",
            "avg_preparing_time", "min_order_amount",
            "is_open",
        )
    
    def validate_min_order_amount(self,value):
        if value<0:
            raise ValidationError('Min price cannot be less than 0')
        return value
    
    def validate(self,attrs):
        request = self.context['request']

        if not self.instance and request:
            count =Restaurants.objects.filter(owner=request.user).count()
            if count>=5:
                raise ValidationError('max 5 restaurants allowed per owner')
        return attrs
    
    def create(self,validated_data):
        request = self.context['request']
        return Restaurants.objects.create(owner=request.user,**validated_data)
    