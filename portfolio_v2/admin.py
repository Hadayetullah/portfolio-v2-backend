from django.contrib import admin
from .models import CustomUser, UserMessageContents, OTPCode

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(UserMessageContents)
admin.site.register(OTPCode)
