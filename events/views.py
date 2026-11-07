
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from accounts.models import StudentProfile
from qr.models import StudentQR
from .models import Attendance


class QRAttendanceView(APIView):
    """
    Mark attendance by scanning the student's permanent QR code.
    """

    permission_classes = [AllowAny]

    def post(self, request):

        qr_token = request.data.get("qr_token")

        if not qr_token:
            return Response(
                {"message": "QR token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        qr = get_object_or_404(
            StudentQR.objects.select_related("student__user"),
            qr_token=qr_token
        )

        student = qr.student

        if not student.is_email_verified or not student.user.is_active:
            return Response(
                {"message": "Student account is not verified or active"},
                status=status.HTTP_403_FORBIDDEN
            )

        return self.record_attendance(student, "QR")

    def record_attendance(self, student, method):
        try:
            with transaction.atomic():
                attendance, created = Attendance.objects.get_or_create(
                    student=student,
                    defaults={"attendance_method": method}
                )

            if not created:
                return Response(
                    {
                        "message": "Attendance already marked",
                        "attendance_method": attendance.attendance_method,
                        "check_in_time": attendance.check_in_time
                    },
                    status=status.HTTP_409_CONFLICT
                )

            return Response(
                {
                    "message": "Attendance marked successfully",
                    "student": str(student),
                    "attendance_method": attendance.attendance_method,
                    "check_in_time": attendance.check_in_time
                },
                status=status.HTTP_201_CREATED
            )

        except IntegrityError:
            return Response(
                {"message": "Attendance already marked"},
                status=status.HTTP_409_CONFLICT
            )


class ManualAttendanceView(APIView):
    """
    Mark attendance manually using the student's student number.
    """

    permission_classes = [AllowAny]

    def post(self, request):

        student_no = request.data.get("student_no")

        if not student_no:
            return Response(
                {"message": "Student number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        student = get_object_or_404(
            StudentProfile.objects.select_related("user"),
            student_no=student_no
        )

        if not student.is_email_verified or not student.user.is_active:
            return Response(
                {"message": "Student account is not verified or active"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            with transaction.atomic():
                attendance, created = Attendance.objects.get_or_create(
                    student=student,
                    defaults={"attendance_method": "MANUAL"}
                )

            if not created:
                return Response(
                    {
                        "message": "Attendance already marked",
                        "attendance_method": attendance.attendance_method,
                        "check_in_time": attendance.check_in_time
                    },
                    status=status.HTTP_409_CONFLICT
                )

            return Response(
                {
                    "message": "Manual attendance marked successfully",
                    "student": str(student),
                    "attendance_method": attendance.attendance_method,
                    "check_in_time": attendance.check_in_time
                },
                status=status.HTTP_201_CREATED
            )

        except IntegrityError:
            return Response(
                {"message": "Attendance already marked"},
                status=status.HTTP_409_CONFLICT
            )


class AttendanceListView(APIView):
    """
    Get all attendance records.
    """

    permission_classes = [AllowAny]

    def get(self, request):

        attendance_records = Attendance.objects.select_related(
            "student", "student__user"
        )

        data = []

        for record in attendance_records:
            student = record.student

            data.append({
                "student_no": student.student_no,
                "name": student.name,
                "roll_no": student.roll_no,
                "section": student.section,
                "year": student.year,
                "attendance_method": record.attendance_method,
                "check_in_time": record.check_in_time
            })

        return Response(
            {
                "total_attendance": len(data),
                "attendance": data
            },
            status=status.HTTP_200_OK
        )


class AttendanceSummaryView(APIView):
    """
    Get attendance statistics.
    """

    permission_classes = [AllowAny]

    def get(self, request):

        total_attendance = Attendance.objects.count()

        qr_attendance = Attendance.objects.filter(
            attendance_method="QR"
        ).count()

        manual_attendance = Attendance.objects.filter(
            attendance_method="MANUAL"
        ).count()

        total_verified_students = StudentProfile.objects.filter(
            is_email_verified=True,
            user__is_active=True
        ).count()

        return Response(
            {
                "total_verified_students": total_verified_students,
                "total_attendance": total_attendance,
                "qr_attendance": qr_attendance,
                "manual_attendance": manual_attendance,
                "absent_students": max(
                    total_verified_students - total_attendance, 0
                )
            },
            status=status.HTTP_200_OK
        )
