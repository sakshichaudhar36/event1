
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from import_export import resources, fields

from .models import StudentProfile


class StudentProfileResource(resources.ModelResource):

    email = fields.Field(column_name="email")

    class Meta:
        model = StudentProfile

        fields = (
            "name",
            "email",
            "branch",
            "section",
            "year",
            "residence",
            "gender",
            "phone_no",
            "roll_no",
            "student_no",
        )

        export_order = (
            "name",
            "email",
            "branch",
            "section",
            "year",
            "residence",
            "gender",
            "phone_no",
            "roll_no",
            "student_no",
        )

    def dehydrate_email(self, student):
        return student.user.email

    def before_import_row(self, row, **kwargs):

        required_fields = [
            "name", "email", "branch", "section",
            "year", "residence", "gender",
            "phone_no", "roll_no", "student_no"
        ]

        # Check required fields and remove surrounding spaces
        for field in required_fields:
            value = row.get(field)

            if value is None or not str(value).strip():
                raise ValueError(f"{field} is required.")

            row[field] = str(value).strip()

        email = row["email"].lower()
        row["email"] = email

        try:
            validate_email(email)
        except ValidationError:
            raise ValueError("Invalid email address.")

        if email.rsplit("@", 1)[-1] != "akgec.ac.in":
            raise ValueError(
                "Only AKGEC college email addresses are allowed."
            )

        if User.objects.filter(email__iexact=email).exists():
            raise ValueError("Email already registered.")

        if User.objects.filter(username__iexact=email).exists():
            raise ValueError("Username already exists.")

        if StudentProfile.objects.filter(
            roll_no__iexact=row["roll_no"]
        ).exists():
            raise ValueError("Roll number already registered.")

        if StudentProfile.objects.filter(
            student_no__iexact=row["student_no"]
        ).exists():
            raise ValueError("Student number already registered.")

        phone = row["phone_no"]

        if not phone.isdigit() or len(phone) != 10:
            raise ValueError(
                "Phone number must contain exactly 10 digits."
            )

        if row["year"] not in dict(StudentProfile.YEAR_CHOICES):
            raise ValueError("Invalid year.")

        if row["residence"] not in dict(StudentProfile.RESIDENCE_CHOICES):
            raise ValueError("Invalid residence.")

        if row["gender"] not in dict(StudentProfile.GENDER_CHOICES):
            raise ValueError("Invalid gender.")

    def before_save_instance(self, instance, row, **kwargs):

        email = row["email"].strip().lower()

        user = User.objects.create_user(
            username=email,
            email=email,
            is_active=False,
        )

        instance.user = user
        instance.is_email_verified = False
