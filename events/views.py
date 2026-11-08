
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from accounts.models import StudentProfile
from qr.models import StudentQR
from .models import Attendance


# --------------------------------------------------
# HELPER: STUDENT DETAILS
# --------------------------------------------------

def get_student_details(student):
    return {
        "student_no": student.student_no,
        "name": student.name,
        "roll_no": student.roll_no,
        "section": student.section,
        "year": student.year,
    }


# --------------------------------------------------
# HELPER: CHECK STUDENT ACCOUNT
# --------------------------------------------------

def is_student_active(student):
    return student.is_email_verified and student.user.is_active


# --------------------------------------------------
# HELPER: MARK ATTENDANCE
# --------------------------------------------------

def mark_student_attendance(student, method):

    try:
        with transaction.atomic():

            attendance, created = Attendance.objects.get_or_create(
                student=student,
                defaults={
                    "attendance_method": method
                }
            )

        if not created:
            return Response(
                {
                    "message": "Attendance already marked",
                    "student": get_student_details(student),
                    "attendance_method": attendance.attendance_method,
                    "check_in_time": attendance.check_in_time,
                },
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            {
                "message": "Attendance marked successfully",
                "student": get_student_details(student),
                "attendance_method": attendance.attendance_method,
                "check_in_time": attendance.check_in_time,
            },
            status=status.HTTP_201_CREATED
        )

    except IntegrityError:

        return Response(
            {
                "message": "Attendance already marked"
            },
            status=status.HTTP_409_CONFLICT
        )


# --------------------------------------------------
# API 1: QR TOKEN LOOKUP
# --------------------------------------------------

class QRStudentLookupView(APIView):

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

        if not is_student_active(student):
            return Response(
                {"message": "Student account is not verified or active"},
                status=status.HTTP_403_FORBIDDEN
            )

        attendance = Attendance.objects.filter(
            student=student
        ).first()

        return Response(
            {
                "message": "Student found",
                "student": get_student_details(student),
                "attendance_marked": attendance is not None,
                "attendance": (
                    {
                        "attendance_method": attendance.attendance_method,
                        "check_in_time": attendance.check_in_time,
                    }
                    if attendance else None
                ),
            },
            status=status.HTTP_200_OK
        )


# --------------------------------------------------
# API 2: STUDENT NUMBER LOOKUP
# --------------------------------------------------

class StudentLookupView(APIView):

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

        if not is_student_active(student):
            return Response(
                {"message": "Student account is not verified or active"},
                status=status.HTTP_403_FORBIDDEN
            )

        attendance = Attendance.objects.filter(
            student=student
        ).first()

        return Response(
            {
                "message": "Student found",
                "student": get_student_details(student),
                "attendance_marked": attendance is not None,
                "attendance": (
                    {
                        "attendance_method": attendance.attendance_method,
                        "check_in_time": attendance.check_in_time,
                    }
                    if attendance else None
                ),
            },
            status=status.HTTP_200_OK
        )


# --------------------------------------------------
# API 3: MARK ATTENDANCE USING QR TOKEN
# --------------------------------------------------

class QRAttendanceView(APIView):

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

        if not is_student_active(student):
            return Response(
                {"message": "Student account is not verified or active"},
                status=status.HTTP_403_FORBIDDEN
            )

        return mark_student_attendance(student, "QR")


# --------------------------------------------------
# API 4: MARK ATTENDANCE USING STUDENT NUMBER
# --------------------------------------------------

class ManualAttendanceView(APIView):

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

        if not is_student_active(student):
            return Response(
                {"message": "Student account is not verified or active"},
                status=status.HTTP_403_FORBIDDEN
            )

        return mark_student_attendance(student, "MANUAL")


# --------------------------------------------------
# API 5: GET ALL ATTENDANCE RECORDS
# --------------------------------------------------

class AttendanceListView(APIView):

    permission_classes = [AllowAny]

    def get(self, request):

        records = Attendance.objects.select_related(
            "student",
            "student__user"
        )

        data = []

        for record in records:

            student = record.student

            data.append(
                {
                    **get_student_details(student),
                    "attendance_method": record.attendance_method,
                    "check_in_time": record.check_in_time,
                }
            )

        return Response(
            {
                "total_attendance": len(data),
                "attendance": data,
            },
            status=status.HTTP_200_OK
        )


# --------------------------------------------------
# API 6: ATTENDANCE SUMMARY
# --------------------------------------------------

class AttendanceSummaryView(APIView):

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
                    total_verified_students - total_attendance,
                    0
                ),
            },
            status=status.HTTP_200_OK
        )
