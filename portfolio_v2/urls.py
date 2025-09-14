
from django.urls import path
from .views import ManualSignupView, OTPVerificationView, ProcessUserMessageView, SocialAuthView

urlpatterns = [
    path('signup/', ManualSignupView.as_view(), name='signup_user'),
    path('otp-verification/', OTPVerificationView.as_view(), name='otp_verification'),
    path('social-auth/', SocialAuthView.as_view(), name='process_user_message'),
    path('process-message/', ProcessUserMessageView.as_view(), name='process_user_message'),
]