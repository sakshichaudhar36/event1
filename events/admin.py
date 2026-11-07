
from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "attendance_method",
        "check_in_time",
    )

    list_filter = (
        "attendance_method",
        "check_in_time",
    )

    search_fields = (
        "student__name",
        "student__student_no",
        "student__roll_no",
    )

    readonly_fields = (
        "student",
        "attendance_method",
        "check_in_time",
    )

    ordering = ("-check_in_time",)
