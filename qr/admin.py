
from django.contrib import admin
from .models import StudentQR


@admin.register(StudentQR)
class StudentQRAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "qr_token",
        "created_at",
    )

    search_fields = (
        "student__name",
        "student__student_no",
        "qr_token",
    )

    readonly_fields = (
        "qr_token",
        "created_at",
    )