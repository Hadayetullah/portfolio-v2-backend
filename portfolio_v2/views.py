import json
from django.contrib.auth import get_user_model
from django.views import View
from django.http import JsonResponse

# Create your views here.
User = get_user_model()

def _parse_json_or_post(request):
    try:
        return json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return request.POST
    

class ManualSignupView(View):
    def post(self, request):
        data = _parse_json_or_post(request)
        provider = data.get('provider')
        if provider != "manual":
            return JsonResponse({"error": "Invalid action"}, status=400)
        
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        purpose = data.get('purpose')
        message = data.get('message')

        user = User.objects.filter(email=email).first()
        if user:
            if user.is_verified and user.is_active:
                pass # data will be saved
            else:
                pass # send otp email
