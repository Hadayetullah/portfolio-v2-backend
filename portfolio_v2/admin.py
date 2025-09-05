from django.contrib import admin
from .models import CustomUser, UserMessageContents, OTPCode, AuthProvider

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(UserMessageContents)
admin.site.register(OTPCode)
admin.site.register(AuthProvider)
