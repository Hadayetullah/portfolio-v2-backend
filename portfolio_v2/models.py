from django.utils import timezone
from datetime import timedelta

from django.db import models

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# Create your models here.
class CustomUserManager(BaseUserManager):
    def _create_user(self, name, email, phone, password=None, **extra_fields):
        if not email:
            raise ValueError('A valid email address is required')

        email = self.normalize_email(email)

        user = self.model(
            name=name,
            email=email,
            phone=phone,
            **extra_fields
        )

        user.set_password(password)

        user.save(using=self._db)
        return user

    def create_user(self, name=None, email=None, phone=None, password=None, **extra_fields):
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(name, email, phone, password, **extra_fields)

    def create_superuser(self, name=None, email=None, phone=None, password=None, **extra_fields):
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if password is None:
            raise ValueError('Superusers must have a password.')

        return self._create_user(name, email, phone, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    # Status flags
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.email



class AuthProvider(models.Model):
    PROVIDERS = [
        ('manual', 'Manual'),
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('github', 'GitHub'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='auth_providers')
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    provider_details = models.JSONField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'provider'], name='unique_user_provider')
        ]

        ordering = ['-created']

    def __str__(self):
        return f"{self.user.email} - {self.provider}"



class UserMessageContents(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='messages', blank=True, null=True)
    purpose = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return self.purpose or "No purpose"



# OTP verification (for manual signup only)
class OTPCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otp_codes')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def otp_is_valid(self):
        """Check if OTP exists and is still valid."""
        if self.otp_code and self.created_at:
            return timezone.now() < self.created_at + timedelta(minutes=5)
        return False

    def __str__(self):
        return f"OTP for {self.user.email}: {self.otp_code}"

