
from django.utils import timezone
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# Create your models here.
class ManualUserManager(BaseUserManager):
    def _create_user(self, name, email, **extra_fields):
        if not email:
            raise ValueError('You have not specified a valid email address')
        email = self.normalize_email(email)
        user = self.model(name=name, email=email, **extra_fields)
        user.save(using=self.db)

        return user
    
    def create_user(self, name=None, email=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(name, email, **extra_fields)

    def create_superuser(self, name=None, email=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(name, email, **extra_fields)


class ManualUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    # OTP fields
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    # Status flags
    is_verified = models.BooleanField(default=False)

    objects = ManualUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['name',]


    def otp_is_valid(self):
        """Checks if the OTP is valid and not expired."""
        if self.otp and self.otp_created_at:
            return timezone.now() < self.otp_created_at + timedelta(minutes=5)
        return False
    

class SocialUserManager(BaseUserManager):
    def _create_user(self, name, email, **extra_fields):
        if not email:
            raise ValueError('You have not specified a valid email address')
        email = self.normalize_email(email)
        user = self.model(name=name, email=email, **extra_fields)
        user.save(using=self.db)

        return user
    
    def create_user(self, name=None, email=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(name, email, **extra_fields)
    

class SocialUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Status flags
    is_verified = models.BooleanField(default=False)

    objects = SocialUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['name',]


class UserMessageContents(models.Model):
    manual_user = models.ForeignKey(ManualUser, on_delete=models.CASCADE, related_name='manual_user_messages', blank=True, null=True)
    social_user = models.ForeignKey(SocialUser, on_delete=models.CASCADE, related_name='social_user_messages', blank=True, null=True)
    purpose = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

