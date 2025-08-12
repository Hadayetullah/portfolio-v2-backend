
from django.urls import path
from .views import ManualSignupView

urlpatterns = [
    path('manual/', ManualSignupView.as_view(), name='manual_user_data'),
]