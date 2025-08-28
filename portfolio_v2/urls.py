
from django.urls import path
from .views import ManualSignupView, OTPVerificationView

urlpatterns = [
    path('manual/', ManualSignupView.as_view(), name='manual_user_data'),
    path('otp-verification/', OTPVerificationView.as_view(), name='otp_verification'),
]