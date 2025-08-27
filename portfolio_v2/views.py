import random
from django.utils import timezone
from django.db import transaction, IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth import get_user_model
from .models import UserAuthProvider, UserMessageContents, OTPCode
from .utils import _send_otp_email

User = get_user_model()


class ManualSignupView(APIView):
    authentication_classes = []  # no auth needed for signup
    permission_classes = []      # open endpoint

    def get(self, request):
        data = request.data
        email = data.get("email")
        otp_code = data.get("otp_code")

        if not email or not otp_code:
            return Response(
                {"error": "Email and otp_code are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            # Get the matching OTP for the user
            otp_obj = OTPCode.objects.filter(user=user, otp_code=otp_code).order_by("-created_at").first()
            print("otp_obj : ", otp_obj)
            if not otp_obj:
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

            # Check if still valid
            if not otp_obj.otp_is_valid():
                return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

            # ✅ Mark user verified and active
            user.is_verified = True
            user.is_active = True
            user.save(update_fields=["is_verified", "is_active"])

            return Response({
                "message": "OTP verified successfully",
                "email": user.email,
                "verified": True,
                "active": True
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        purpose = data.get('purpose')
        message = data.get('message')

        try:
            with transaction.atomic():
                user = User.objects.filter(email=email).first()

                # 3️⃣ Existing verified user → Save message only
                if user and user.is_verified and user.is_active:
                    try:
                        provider_obj, _ = user.add_provider(provider)
                        UserMessageContents.objects.create(
                            provider=provider_obj,
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

                # 4️⃣ Existing but unverified/inactive user → resend OTP
                elif user and (not user.is_verified or not user.is_active):
                    otp_code = f"{random.randint(100000, 999999)}"
                    OTPCode.objects.create(user=user, otp_code=otp_code)
                    user.add_provider(provider)

                    _send_otp_email(user, otp_code)

                    return Response({
                        "message": "OTP sent to existing user",
                        "email": email,
                        "verified": False,
                        "active": False
                    }, status=status.HTTP_200_OK)

                # 5️⃣ New user → Create and send OTP
                else:
                    otp_code = f"{random.randint(100000, 999999)}"
                    user = User.objects.create(
                        email=email,
                        name=name,
                        phone=phone,
                        is_verified=False,
                        is_active=False,
                    )
                    user.add_provider(provider)

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
