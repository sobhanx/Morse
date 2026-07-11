from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from .utils import generate_new_verify_code
from .validators import phone_number_validator


class CustomUserManager(UserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("The phone field must be set")

        if "email" not in extra_fields or not extra_fields["email"]:
            extra_fields["email"] = None

        if "username" not in extra_fields:
            extra_fields["username"] = phone

        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        extra_fields.setdefault("username", phone)

        if "email" not in extra_fields or not extra_fields["email"]:
            extra_fields["email"] = None

        return self.create_user(phone=phone, password=password, **extra_fields)


class User(AbstractUser):
    phone = models.CharField(
        "تلفن همراه",
        max_length=11,
        unique=True,
        validators=[phone_number_validator],
    )
    valid_phone = models.BooleanField("تایید تلفن همراه", default=False)
    email = models.EmailField("ایمیل", unique=True, null=True, blank=True)

    REQUIRED_FIELDS = []
    USERNAME_FIELD = "phone"
    objects = CustomUserManager()

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        if self.get_full_name():
            return self.get_full_name()
        return self.phone

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__previous_phone = self.phone

    def save(self, *args, **kwargs):
        if not self.email:
            self.email = None
        if self.__previous_phone != self.phone:
            self.valid_phone = False
        super().save(*args, **kwargs)


class VerifyCode(models.Model):
    SUBJECT_CHOICES = [
        ("phone", "تلفن همراه"),
        ("email", "ایمیل"),
    ]
    STATUS_CHOICES = [
        (0, "نامعتبر"),
        (1, "معتبر"),
        (2, "اعمال شده"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    code = models.CharField(
        max_length=10,
        blank=True,
        editable=False,
        unique=True,
        default=generate_new_verify_code,
    )
    status = models.PositiveSmallIntegerField(default=1, choices=STATUS_CHOICES)
    attempts = models.PositiveSmallIntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = "کد تایید"
        verbose_name_plural = "کدهای تایید"

    def __str__(self):
        return f"{self.subject} - {self.code}"


class SmsLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    subject = models.CharField(max_length=30, default="other")
    is_sent = models.BooleanField(default=True)
    status_code = models.PositiveSmallIntegerField(null=True)

    class Meta:
        verbose_name = "تاریخچه SMS"
        verbose_name_plural = "تاریخچه SMS"

    def __str__(self):
        return f"{self.subject} - {self.phone}"
