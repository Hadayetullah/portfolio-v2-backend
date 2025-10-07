import requests
import random
from django.db import transaction, IntegrityError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth import get_user_model
from .models import UserMessageContents, OTPCode
from .utils import _send_otp_email, _get_email_client, generate_access_token


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
                    user.auth_providers.get_or_create(provider=provider, defaults={"provider_details": None})
                    OTPCode.objects.create(user=user, otp_code=otp_code)
                    _send_otp_email(user, otp_code)

                # New user → Create and send OTP
                else:
                    user = User.objects.create(
                        email=email,
                        name=name,
                        phone=phone,
                        is_verified=False,
                        is_active=False
                    )

                    user.auth_providers.create(provider=provider, provider_details=None)

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

        name = data.get('name')
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

                    _get_email_client(email, name, purpose, message)

                    access_token = generate_access_token(user)
                    return Response({
                        "message": "Thank you for your message. I will get back to you soon.",
                        "verified": True,
                        "active": True,
                        "token": access_token
                    }, status=status.HTTP_200_OK)
                except IntegrityError:
                    return Response({"error": "Could not save message"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class SocialAuthView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        provider = request.data.get("provider")
        token = request.data.get("access_token")
        provider_details = request.data.get("provider_details")

        if not provider or not token:
            return Response(
                {"error": "Provider and access_token are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email, name = None, None

        try:
            if provider == "google":
                # ✅ Google UserInfo endpoint
                resp = requests.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )
                data = resp.json()
                if "error" in data or "email" not in data:
                    return Response(
                        {"error": "Invalid Google token"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                email = data.get("email")
                name = data.get("name")

            elif provider == "facebook":
                # ✅ Facebook Graph API
                resp = requests.get(
                    f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}"
                )
                data = resp.json()
                if "error" in data:
                    return Response(
                        {"error": "Invalid Facebook token"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                email = data.get("email")
                name = data.get("name")

            elif provider == "github":
                # ✅ GitHub API
                resp = requests.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {token}"},
                )
                data = resp.json()
                
                if "id" not in data:
                    return Response(
                        {"error": "Invalid GitHub token"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                email = data.get("email")  # sometimes null if user hides email

                if not email:  # fallback if email is hidden
                    emails_resp = requests.get(
                        "https://api.github.com/user/emails",
                        headers={"Authorization": f"token {token}"},
                    )
                    emails_data = emails_resp.json()
                    for e in emails_data:
                        if e.get("primary") and e.get("verified"):
                            email = e["email"]
                            break

            else:
                return Response(
                    {"error": "Unsupported provider"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            
            try:
                user, created = User.objects.get_or_create(
                    email=email,
                    is_verified=True,
                    is_active=True
                )

                if created:
                    user.auth_providers.create(provider=provider, provider_details=provider_details)
                elif user and not created:
                    provider_user, _ = user.auth_providers.get_or_create(provider=provider)
                    provider_user.provider_details = provider_details
                    provider_user.save(update_fields=['provider_details'])
                

            except IntegrityError as e:
                return Response({"error": f"Database error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            access_token = generate_access_token(user)
            return Response({
                "message": "Verification successful.",
                "verified": True,
                "active": True,
                "access_token": access_token
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)



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

                        _get_email_client(email, name, purpose, message)

                        return Response({
                            "message": "Thank you for your message. I will get back to you soon.",
                            "verified": True,
                            "active": True,
                        }, status=status.HTTP_200_OK)
                        
                    except IntegrityError:
                        return Response({"error": "Could not save message"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except IntegrityError as e:
            return Response({"error": f"Database error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
