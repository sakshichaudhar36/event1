
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class StudentProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=100)

    branch = models.CharField(max_length=100)

    section = models.CharField(max_length=20)

    YEAR_CHOICES = [
        ("1st Year", "1st Year"),
        ("2nd Year", "2nd Year"),
        ("3rd Year", "3rd Year"),
        ("4th Year", "4th Year"),
    ]

    year = models.CharField(
        max_length=20,
        choices=YEAR_CHOICES
    )

    RESIDENCE_CHOICES = [
        ("Hosteller", "Hosteller"),
        ("Day Scholar", "Day Scholar"),
    ]

    residence = models.CharField(
        max_length=20,
        choices=RESIDENCE_CHOICES
    )

    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    phone_no = models.CharField(max_length=10)

    roll_no = models.CharField(
        max_length=30,
        unique=True
    )

    student_no = models.CharField(
        max_length=30,
        unique=True
    )

    is_email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class EmailOTP(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    otp = models.CharField(max_length=6)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.email}"


class PendingRegistration(models.Model):

    registration_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    registration_data = models.JSONField()

    otp_hash = models.CharField(max_length=128)

    attempts = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    otp_expires_at = models.DateTimeField()

    otp_last_sent_at = models.DateTimeField(default=timezone.now)

    registration_expires_at = models.DateTimeField()

    def __str__(self):
        return str(self.registration_id)
