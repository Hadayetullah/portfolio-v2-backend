import json
import random

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import get_user_model
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction, IntegrityError

from .models import UserAuthProvider, UserMessageContents

# Create your views here.
User = get_user_model()

def _parse_json_or_post(request):
    try:
        return json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return request.POST
    

@method_decorator(csrf_exempt, name='dispatch')
class ManualSignupView(View):
    def post(self, request):
        try:
            data = _parse_json_or_post(request)
        except Exception:
            return JsonResponse({"error": "Invalid request body"}, status=400)
        
        # 1️⃣ Validate provider
        provider = data.get('provider')
        if provider != "manual":
            return JsonResponse({"error": "Invalid provider"}, status=400)
        
        # 2️⃣ Required fields validation
        email = data.get('email')
        if not email:
            return JsonResponse({"error": "Email is required"}, status=400)
            
        name = data.get('name')
        phone = data.get('phone')
        purpose = data.get('purpose')
        message = data.get('message')

        try:
            with transaction.atomic():

                user = User.objects.filter(email=email).first()

                # 3️⃣ Case: Existing verified user → Save message only
                if user and user.is_verified and user.is_active:
                    try:
                        provider_obj, _ = user.add_provider(provider)
                        UserMessageContents.objects.create(
                            provider=provider_obj,
                            user=user,
                            purpose=purpose,
                            message=message
                        )

                        return JsonResponse({
                            "message": "Message saved for existing user",
                            "verified": True,
                            "active": True
                            }, status=200)
                    
                    except IntegrityError:
                        return JsonResponse({"error": "Could not save message"}, status=500)
                    
                elif user and (not user.is_verified or not user.is_active):
                    otp_code = f"{random.randint(100000, 999999)}"
                    user.otp = otp_code
                    user.otp_created_at = timezone.now()
                    user.save(update_fields=['otp', 'otp_created_at'])
                    user.add_provider(provider)
                    # TODO: Send OTP email
                    return JsonResponse({
                        "message": "OTP sent to existing user",
                        "email": email,
                        "verified": False,
                        "active": False
                        }, status=200)
                
                # 5️⃣ Case: New user → Create user and send OTP
                else:
                    otp_code = f"{random.randint(100000, 999999)}"
                    user = User.objects.create(
                        email=email,
                        name=name,
                        phone=phone,
                        is_verified=False,
                        is_active=False,
                        otp=otp_code,
                        otp_created_at=timezone.now()
                    )

                    user.save()
                    user.add_provider(provider)
                    # TODO: Send OTP email

                    return JsonResponse({
                        "message": "User created and OTP sent",
                        "email": email,
                        "verified": False,
                        "active": False
                        }, status=201)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)
