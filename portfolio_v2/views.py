import random
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth import get_user_model
from .models import UserMessageContents, OTPCode
from .utils import _send_otp_email

User = get_user_model()


class ManualSignupView(APIView):
    authentication_classes = []  # no auth needed for signup
    permission_classes = []      # open endpoint

    def post(self, request):
        data = request.data  

        # 1️⃣ Validate provider
        provider = data.get('provider')
        if provider != "manual":
            return Response({"error": "Invalid provider"}, status=status.HTTP_400_BAD_REQUEST)

        # 2️⃣ Required fields
        email = data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        name = data.get('name')
        phone = data.get('phone')

        try:
            with transaction.atomic():
                otp_code = f"{random.randint(100000, 999999)}"

                # Send otp
                user = User.objects.filter(email=email).first()
                if user:
                    user.save(update_fields=['name', 'phone'])
                    OTPCode.objects.create(user=user, otp_code=otp_code)
                    _send_otp_email(user, otp_code)

                # New user → Create and send OTP
                else:
                    user = User.objects.create(
                        email=email,
                        name=name,
                        phone=phone,
                        is_verified=True,
                        is_active=True
                    )

                    user.auth_providers.create(provider=provider, provider_details={})

                    OTPCode.objects.create(user=user, otp_code=otp_code)
                    _send_otp_email(user, otp_code)

                return Response({
                    "message": "User created and OTP sent",
                    "email": email,
                    "verified": False,
                    "active": False
                }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            return Response({"error": f"Database error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class OTPVerificationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        data = request.data
        email = data.get("email")
        otp_code = data.get("otp_code")

        purpose = data.get('purpose')
        message = data.get('message')

        if not email or not otp_code:
            return Response(
                {"error": "Email and otp_code are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        provider = data.get('provider')
        if provider != "manual":
            return Response({"error": "Invalid provider"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                user = User.objects.filter(email=email).first()
                if not user:
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

                # Get the matching OTP for the user
                otp_obj = OTPCode.objects.filter(user=user, otp_code=otp_code).order_by("-created_at").first()
                
                if not otp_obj:
                    return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

                # Check if still valid
                if not otp_obj.otp_is_valid():
                    return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

                # ✅ Mark user verified and active
                user.is_verified = True
                user.is_active = True
                user.save(update_fields=["is_verified", "is_active"])

                # ❌ Delete all OTPs after success
                OTPCode.objects.filter(user=user).delete()
                
                try:
                    UserMessageContents.objects.create(
                        user=user,
                        purpose=purpose,
                        message=message
                    )
                    return Response({
                        "message": "Thank you for your message. I will get back to you soon.",
                        "verified": True,
                        "active": True
                    }, status=status.HTTP_200_OK)
                except IntegrityError:
                    return Response({"error": "Could not save message"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class ProcessUserMessageView(APIView):
    authentication_classes = [JWTAuthentication]  # DRF will decode the Bearer token
    permission_classes = [IsAuthenticated]      # Ensures token is required

    def post(self, request):
        data = request.data  

        # 1️⃣ Validate provider
        provider = data.get('provider')
        if not provider:
            return Response({"error": "Invalid provider"}, status=status.HTTP_400_BAD_REQUEST)

        # 2️⃣ Required fields
        email = data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        name = data.get('name')
        phone = data.get('phone')
        provider_details = data.get('provider_details')
        purpose = data.get('purpose')
        message = data.get('message')

        try:
            with transaction.atomic():
                user = User.objects.filter(email=email).first()

                # 3️⃣ Existing verified user → Save message only
                if user:
                    user.name = name or user.name
                    user.phone = phone or user.phone
                    user.is_verified = True
                    user.is_active = True
                    user.save()

                    user.auth_providers.get_or_create(
                        provider=provider,
                        defaults={"provider_details": provider_details}
                    )

                    try:
                        UserMessageContents.objects.create(
                            user=user,
                            purpose=purpose,
                            message=message
                        )
                        return Response({
                            "message": "Thank you for your message. I will get back to you soon.",
                            "verified": True,
                            "active": True
                        }, status=status.HTTP_200_OK)
                    except IntegrityError:
                        return Response({"error": "Could not save message"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except IntegrityError as e:
            return Response({"error": f"Database error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
