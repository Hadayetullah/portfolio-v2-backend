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
        user = self.model(name=name, email=email, phone=phone, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # Safely disable password login

        user.save(using=self._db)
        return user

    def create_user(self, name=None, email=None, phone=None, **extra_fields):
        """Normal user creation — no password unless explicitly given."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        # Passwordless by default
        return self._create_user(name, email, phone, password=None, **extra_fields)

    def create_superuser(self, name=None, email=None, phone=None, password=None, **extra_fields):
        """Superuser creation — password required."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if password is None:
            raise ValueError('Superusers must have a password.')

        return self._create_user(name, email, phone, password=password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    # OTP fields (for manual signup only)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    # Status flags
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        ordering = ['created']

    def otp_is_valid(self):
        """Check if OTP exists and is still valid."""
        if self.otp and self.otp_created_at:
            return timezone.now() < self.otp_created_at + timedelta(minutes=5)
        return False

    def __str__(self):
        return self.email
    

class UserAuthProvider(models.Model):
    PROVIDERS = [
        ('manual', 'manual'),
        ('google', 'google'),
        ('facebook', 'facebook'),
        ('github', 'github'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="auth_providers")
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    uid = models.CharField(max_length=255, blank=True, null=True)  # Social provider user ID
    extra_data = models.JSONField(blank=True, null=True)  # store profile data from social login

    class Meta:
        unique_together = ('user', 'provider')  # No duplicate provider for same user

    def __str__(self):
        return f"{self.user.email} - {self.provider}"



class UserMessageContents(models.Model):
    user = models.ForeignKey(UserAuthProvider, on_delete=models.CASCADE, related_name='user_messages', blank=True, null=True)
    purpose = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return self.purpose

