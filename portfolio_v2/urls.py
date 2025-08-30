
from django.urls import path
from .views import ManualSignupView, OTPVerificationView

urlpatterns = [
    path('signup/', ManualSignupView.as_view(), name='signup_user'),
    path('otp-verification/', OTPVerificationView.as_view(), name='otp_verification'),
]