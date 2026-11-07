
from django.db import models
from django.db.models import Q


class Attendance(models.Model):

    ATTENDANCE_METHOD_CHOICES = [
        ("QR", "QR Code"),
        ("MANUAL", "Manual Entry"),
    ]

    student = models.OneToOneField(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,
        related_name="attendance"
    )

    attendance_method = models.CharField(
        max_length=10,
        choices=ATTENDANCE_METHOD_CHOICES
    )

    check_in_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-check_in_time"]

    def __str__(self):
        return f"{self.student} - {self.attendance_method}"
