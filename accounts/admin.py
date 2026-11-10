from django.contrib import admin

from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import StudentProfile
from .resources import StudentProfileResource


@admin.register(StudentProfile)
class StudentProfileAdmin(ImportExportModelAdmin):

    resource_class = StudentProfileResource

    list_display = (
        "name",
        "user",
        "branch",
        "section",
        "year",
        "roll_no",
        "student_no",
        "is_email_verified",
    )

    search_fields = (
        "name",
        "user__email",
        "roll_no",
        "student_no",
    )

    list_filter = (
        "branch",
        "year",
        "residence",
        "gender",
        "is_email_verified",
    )
    use_transactions = True

# Register your models here.
