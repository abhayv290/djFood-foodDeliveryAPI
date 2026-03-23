from typing import cast
from datetime import timedelta
from django.utils import timezone
from rest_framework import status,generics 
from rest_framework.views   import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from rest_framework.generics import (
    GenericAPIView,RetrieveUpdateDestroyAPIView,
    RetrieveUpdateAPIView,
    ListCreateAPIView
)
from drf_spectacular.utils import extend_schema

from core.permissions import IsCustomer,IsRestaurantOwner,IsDeliveryAgent
from .models import CustomerAddress,DeliveryAgentProfile,EmailVerificationToken
from .serialzers import (
    CustomerRegistrationSerializer,
    RestaurantOwnerRegistrationSerializer,
    DeliveryAgentRegistrationSerializer,
    CustomerProfileSerializer,
    CustomerAddressSerializer,
    RestaurantOwnerProfileSerializer,
    DeliveryAgentProfileSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    ResetPasswordSerializer,
    AgentLocationUpdateSerializer,
    EmailVerificationSerializer,
    ResendVerificationEmailSerializer,
    get_tokens_for_user,
)



def send_verification_email(user,token):

    link  = f"http://localhost:8000/api/v1/auth/email/verify/?token={token}"
    # ── DEV:
    print("\n" + "="*60)
    print(f"  EMAIL VERIFICATION (dev mode)")
    print(f"  To: {user.email}")
    print(f"  Link: {link}")
    print("="*60 + "\n")



def create_verification_token(user):
    EmailVerificationToken.objects.filter(user=user).delete()
    token_obj=EmailVerificationToken.objects.create(user=user,expires_at=timezone.now()+timedelta(hours=24))
    return token_obj.token


@extend_schema(tags=['Register'])
class RegisterView(APIView):
    permission_classes=[AllowAny]
    def post(self,request,serializer):
        ser = serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        #create token and send verification email
        token = create_verification_token(user)
        send_verification_email(user,token)
        return Response({
            'message' : 'Registration successful , Check your email to verify your account',
            'user_id' : str(user[0].id) if isinstance(user, list) else str(user.id),
            'tokens' : get_tokens_for_user(user)
        },
        status=status.HTTP_201_CREATED
    )
        

class CustomerRegisterView(RegisterView):
    @extend_schema(request=CustomerRegistrationSerializer)
    def post(self,request,serializer=CustomerRegistrationSerializer):
        return super().post(request,serializer)
        


class RestaurantOwnerRegisterView(RegisterView):
    @extend_schema(request=RestaurantOwnerRegistrationSerializer)
    def post(self,request,serializer=RestaurantOwnerRegistrationSerializer):
        return super().post(request,serializer)

class DeliveryAgentRegisterView(RegisterView):
    @extend_schema(request=DeliveryAgentRegistrationSerializer)
    def post(self,request,serializer=DeliveryAgentRegistrationSerializer):
        return super().post(request,serializer)



@extend_schema(tags=['Auth'],responses=LoginSerializer)
class LoginView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(request=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = cast(dict, serializer.validated_data)  
        user = validated["user"]

        if not user.is_email_verified:
            return Response({
                'error' : 'Verify your email before login',
                'code' :'email_not_verified',
            },status=status.HTTP_403_FORBIDDEN)
        
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return Response({
            "tokens":    get_tokens_for_user(user),
            "role":      user.role,
            "name":      user.name,
            "user_id":   str(user.id),
        })





@extend_schema(tags=['Auth'])
class LogoutView(APIView):
    '''Blacklisting Refresh Token , So that user cannot generate new access token 
       '''
    def post(self,request):
        try:
            ref_token = request.data.get('refresh')
            token = RefreshToken(ref_token)
            token.blacklist()
            return Response({'message' : 'user logout'})
        except TokenError:
            return Response({
                "success":False,"error" : "Invalid or expired tokens"
            },status=status.HTTP_400_BAD_REQUEST)
        


@extend_schema(tags=['Auth'])
class MeView(APIView):
    '''For fetching Who is logged in'''
    permission_classes = [IsAuthenticated]
    def get(self,request):
        user = request.user
        data = {
            'id' : str(user.id),
            'email' : user.email,
            'phone' : user.phone,
            'name' : user.name,
            'role' :user.role,
            'is_email_verified' : user.is_email_verified,
            'is_phone_verified' : user.is_phone_verified,
        }

    #attaching the profile based on user role 
        if user.is_customer:
            data['profile'] = CustomerProfileSerializer(user.customer_profile).data 
        elif user.is_restaurant_owner:
            data['profile'] = RestaurantOwnerProfileSerializer(user.owner_profile).data
        elif user.is_delivery_agent : 
            data['profile'] = DeliveryAgentProfileSerializer(user.agent_profile).data
        
        return Response(data)
           



#password change
@extend_schema(tags=['Auth'])
class ChangePasswordView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        serializer = ChangePasswordSerializer(data=request.data,context={'request':request})
        serializer.is_valid(raise_exception=True)
        user =request.user 
        user.set_password(serializer.validated_data.get('new_password')) #type:ignore
        user.save(update_fields=['password'])
        return Response({'message' : 'Password Updated'})
    
#TODO 
@extend_schema(tags=['Auth'])
class ResetPassword(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        serializer = ResetPasswordSerializer(data=request.data,context={'request' : request})
        serializer.is_valid(raise_exception=True)
        



@extend_schema(tags=['Profiles-Customer'])
class CustomerProfileView(RetrieveUpdateAPIView):
    permission_classes=[IsAuthenticated,IsCustomer]
    serializer_class = CustomerProfileSerializer

    def get_object(self):
        #returns logged-in users own profile
        return self.request.user.customer_profile  #type:ignore
    



@extend_schema(tags=['Profiles-Customer'])
class CustomerAddressView(ListCreateAPIView):
    permission_classes=[IsAuthenticated,IsCustomer]
    serializer_class = CustomerAddressSerializer

    def get_queryset(self):
        return self.request.user.customer_profile.addresses.all() #type:ignore 
    
    def perform_create(self, serializer):
        serializer.save(customer=self.request.user.customer_profile) #type:ignore


@extend_schema(tags=['Addresses-Customer'])
class CustomerAddressDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes= [IsAuthenticated,IsCustomer]
    serializer_class = CustomerAddressSerializer

    def get_queryset(self):
        return self.request.user.customer_profile.addresses.all() #type:ignore


@extend_schema(tags=['Addresses-Customer'])
class CustomerSetDefaultAddressView(APIView):
    permission_classes=[IsAuthenticated,IsCustomer]
    
    def post(self,request,pk):
       try:
           address = request.user.customer_profile.addresses.get(pk=pk)
       except CustomerAddress.DoesNotExist:
           return Response({'error' : 'Address not found'},status=status.HTTP_404_NOT_FOUND)
       
       address.is_default = True
       address.save()
       return Response({'message' : 'Default Address Updated'})

@extend_schema(tags=['Profiles-Restaurant'])
class RestaurantOwnerProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated,IsRestaurantOwner]
    serializer_class = RestaurantOwnerProfileSerializer

    def get_object(self):
        return self.request.user.owner_profile #type:ignore


@extend_schema(tags=['Profiles-Delivery Agent'])
class DeliveryAgentProfileView(RetrieveUpdateAPIView):
    permission_classes=[IsAuthenticated,IsDeliveryAgent]
    serializer_class = DeliveryAgentProfileSerializer

    def get_object(self):
        return self.request.user.agent_profile #type:ignore
    


@extend_schema(tags=['Profiles-Delivery Agent'])
class DeliveryAgentProfileLocation(APIView):
    permission_classes  = [IsAuthenticated,IsDeliveryAgent]
    """
    Called every few seconds by the agent's app to push GPS coordinates.
    The tracking app's WebSocket consumer will broadcast this to subscribers.
    """
    def post(self,request):
        serializer = AgentLocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data= cast(dict,serializer.validated_data)
        profile = request.user.agent_profile 

        profile.lat = data['lat']
        profile.long = data['long']
        profile.last_location_update = timezone.now()

        if 'status' in data:
            profile.status = data['status']
        
        profile.save(update_fields=['lat','long','last_location_update',
                                    'status'])
        
        return Response({'message' : 'Location Updated'})


@extend_schema(tags=['Profiles-Delivery Agent'])
class AgentAvailabilityView(APIView):
    #Toggle Agent Status Online /offline
    permission_classes = [IsAuthenticated,IsDeliveryAgent]
    
    def patch(self,request):
        is_available = request.data.get('is_available')
        if is_available is None:
            return Response({'error':"is_available field is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        
        profile = request.user.agent_profile
        profile.status =(
            DeliveryAgentProfile.AgentStatus.AVAILABLE 
            if is_available else 
            DeliveryAgentProfile.AgentStatus.OFFLINE
        )

        profile.save(update_fields=['status'])
        return Response({'message' : 'Agent Status Updated'})





#Email Verifications Views
@extend_schema(tags=['Email Service'])
class VerifyEmailView(GenericAPIView):
    """
    GET /api/v1/auth/email/verify/?token=<uuid>
 
    The user clicks the link in their email — this endpoint handles it.
    No auth required because the user may not be logged in when they click.
 
    ── Flow ----------------------------------------------------------------
    1. Extract token from query params
    2. Serializer validates: token exists + not expired + user not already verified
    3. Mark user as verified, delete the token (single-use)
    4. Return success
 
    ── To upgrade later ----------------------------------------------------------------
    In a real frontend flow, this endpoint would redirect to:
        https://frontend.com/verification-success
    For API-only, returning JSON is fine.
    """
    permission_classes = [AllowAny]
    serializer_class = EmailVerificationSerializer
 
    def get(self, request):
        # Token comes from query param: ?token=<uuid>
        serializer = self.get_serializer(
            data={"token": request.query_params.get("token")},
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
 
        token_obj = serializer.context["token_obj"]
        user = token_obj.user
 
        # Mark verified and delete the token atomically
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        token_obj.delete()  # single-use — can never be used again
 
        return Response({"message": "Email verified successfully. You can now log in."})
 
    def get_serializer_context(self):
        return {"request": self.request, "view": self}
 


@extend_schema(tags=['Email Service'])
class ResendVerificationEmailView(GenericAPIView):
    """
    For users who didn't get the email or whose token expired.
    We validate the email, then generate and send a new token.
    """
    permission_classes = [AllowAny]
    serializer_class = ResendVerificationEmailSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data.get("user")
        
        if user:
            token = create_verification_token(user)
            send_verification_email(user, token)

        return Response(
            {"message": "A new verification link has been sent."},
            status=status.HTTP_200_OK
        )
