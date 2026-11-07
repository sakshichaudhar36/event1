import secrets

from django.db import models
from accounts.models import StudentProfile


class StudentQR(models.Model):
    student = models.OneToOneField(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="qr_code"
    )

    qr_token = models.CharField(
        max_length=64,
        unique=True,
        editable=False
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.qr_token:
            self.qr_token = secrets.token_urlsafe(32)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"QR - {self.student.name}"