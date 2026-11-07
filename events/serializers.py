
from rest_framework import serializers
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    student_no = serializers.CharField(
        source="student.student_no",
        read_only=True
    )

    name = serializers.CharField(
        source="student.name",
        read_only=True
    )

    roll_no = serializers.CharField(
        source="student.roll_no",
        read_only=True
    )

    section = serializers.CharField(
        source="student.section",
        read_only=True
    )

    year = serializers.CharField(
        source="student.year",
        read_only=True
    )

    class Meta:
        model = Attendance
        fields = [
            "id",
            "student",
            "student_no",
            "name",
            "roll_no",
            "section",
            "year",
            "attendance_method",
            "check_in_time",
        ]
        read_only_fields = fields
