from django.contrib import admin
from .models import CustomUser, UserAuthProvider, UserMessageContents

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(UserAuthProvider)
admin.site.register(UserMessageContents)
