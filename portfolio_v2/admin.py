from django.contrib import admin
from .models import CustomUser, UserAuthProvider, UserMessageContents, OTPCode

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(UserAuthProvider)
admin.site.register(UserMessageContents)
admin.site.register(OTPCode)
