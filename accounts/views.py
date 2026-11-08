
import logging
import secrets
import uuid
from django.contrib.auth import authenticate
import requests
from django.db import transaction
from django.db.models.deletion import ProtectedError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .permissions import IsSuperUser
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from .models import StudentProfile, EmailOTP
from .serializers import RegisterSerializer

from qr.services import send_student_qr_email


logger = logging.getLogger(__name__)


# --------------------------------------------------
# GOOGLE RECAPTCHA V2 VERIFICATION
# --------------------------------------------------

def verify_recaptcha(captcha_token):

    if not captcha_token:
        return False, ["missing-input-response"]

    secret = getattr(settings, "RECAPTCHA_SECRET_KEY", None)

    if not secret:
        logger.error("RECAPTCHA_SECRET_KEY is not configured")
        return False, ["missing-input-secret"]

    try:

        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": secret,
                "response": captcha_token
            },
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        logger.info("Google CAPTCHA success: %s",
                    result.get("success"))

        return (
            result.get("success", False),
            result.get("error-codes", [])
        )

    except (requests.RequestException, ValueError):

        logger.exception("Google CAPTCHA verification request failed")

        return False, ["verification-request-failed"]


# --------------------------------------------------
# OTP GENERATION
# --------------------------------------------------

def generate_otp():

    return str(secrets.randbelow(900000) + 100000)


# --------------------------------------------------
# SEND OTP EMAIL
# --------------------------------------------------

def send_student_otp(user, name, otp):

    return send_mail(
        subject="AWS Event - Email Verification",

        message=(
            f"Hello {name},\n\n"
            f"Your OTP is {otp}.\n\n"
            "Your OTP expires in 5 minutes.\n\n"
            "AWS Event Team"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,

        recipient_list=[user.email],

        fail_silently=False
    )


# --------------------------------------------------
# SEND QR EMAIL SAFELY
# --------------------------------------------------

def send_qr_email_safely(profile):

    try:

        send_student_qr_email(profile)

    except Exception:

        logger.exception(
            "QR email failed for student %s",
            profile.student_no
        )


# --------------------------------------------------
# REGISTER API
# --------------------------------------------------

class RegisterView(APIView):

    def post(self, request):

        # 1. Validate registration data

        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        # 2. Verify Google reCAPTCHA

        captcha_token = data.get("recaptcha_token")

        captcha_valid, captcha_errors = verify_recaptcha(
            captcha_token
        )

        if not captcha_valid:

            return Response(
                {
                    "success": False,
                    "error": "CAPTCHA verification failed. Please try again.",
                    "details": captcha_errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove CAPTCHA token before saving student details

        data.pop("recaptcha_token")

        email = data["email"].strip().lower()

        # 3. Generate OTP

        otp = generate_otp()

        # 4. Generate unique username

        username_base = slugify(data["name"])[:140] or "student"

        username = f"{username_base}_{uuid.uuid4().hex[:8]}"

        # 5. Create User, StudentProfile and EmailOTP

        try:

            with transaction.atomic():

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=None,
                    is_active=False
                )

                profile = StudentProfile.objects.create(
                    user=user,
                    name=data["name"],
                    section=data["section"],
                    year=data["year"],
                    residence=data["residence"],
                    gender=data["gender"],
                    phone_no=data["phone_no"],
                    roll_no=data["roll_no"],
                    student_no=data["student_no"],
                    is_email_verified=False
                )

                EmailOTP.objects.create(
                    user=user,
                    otp=otp,
                    expires_at=(
                        timezone.now() + timedelta(minutes=5)
                    )
                )

                # Send OTP email

                email_sent = send_student_otp(
                    user,
                    profile.name,
                    otp
                )

                if email_sent != 1:
                    raise RuntimeError("OTP email could not be sent")

        except Exception:

            logger.exception("Student registration failed")

            return Response(
                {
                    "success": False,
                    "error": "Registration failed. Please check your details and try again."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "success": True,
                "message": "Registration successful. OTP sent to your email.",
                "name": profile.name,
                "email": user.email,
                "student_no": profile.student_no
            },
            status=status.HTTP_201_CREATED
        )


# --------------------------------------------------
# VERIFY REGISTRATION OTP API
# --------------------------------------------------

class VerifyOTPView(APIView):

    def post(self, request):

        email = (
            request.data.get("email") or ""
        ).strip().lower()

        student_no = (
            request.data.get("student_no") or ""
        ).strip()

        otp = (
            request.data.get("otp") or ""
        ).strip()

        if not email or not student_no or not otp:

            return Response(
                {
                    "error": "Email, student number and OTP are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            profile = StudentProfile.objects.select_related(
                "user"
            ).get(
                student_no=student_no,
                user__email__iexact=email
            )

        except StudentProfile.DoesNotExist:

            return Response(
                {
                    "error": "Student account not found with these details."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user = profile.user

        if profile.is_email_verified or user.is_active:

            return Response(
                {
                    "message": "This student account is already verified."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            otp_record = EmailOTP.objects.select_for_update().filter(
                user=user
            ).order_by("-created_at").first()

            if otp_record is None:

                return Response(
                    {
                        "error": "OTP not found. Please request a new OTP."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if otp_record.expires_at < timezone.now():

                return Response(
                    {
                        "error": "OTP has expired. Please request a new OTP."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not secrets.compare_digest(
                str(otp_record.otp),
                otp
            ):

                return Response(
                    {
                        "error": "Incorrect OTP."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Activate student account

            profile.is_email_verified = True

            profile.save(
                update_fields=["is_email_verified"]
            )

            user.is_active = True

            user.save(
                update_fields=["is_active"]
            )

            # Delete used OTP

            EmailOTP.objects.filter(
                user=user
            ).delete()

            # Send QR email after database commit

            transaction.on_commit(
                lambda: send_qr_email_safely(profile)
            )

        return Response(
            {
                "success": True,
                "message": "Email verified successfully. Your account is activated.",
                "student_no": profile.student_no,
                "qr_email": "QR email sending was attempted."
            },
            status=status.HTTP_200_OK
        )


# --------------------------------------------------
# RESEND OTP API
# --------------------------------------------------

class ResendOTPView(APIView):

    def post(self, request):

        email = (
            request.data.get("email") or ""
        ).strip().lower()

        student_no = (
            request.data.get("student_no") or ""
        ).strip()

        if not email or not student_no:

            return Response(
                {
                    "error": "Email and student number are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            profile = StudentProfile.objects.select_related(
                "user"
            ).get(
                student_no=student_no,
                user__email__iexact=email
            )

        except StudentProfile.DoesNotExist:

            return Response(
                {
                    "error": "Student account not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user = profile.user

        if profile.is_email_verified or user.is_active:

            return Response(
                {
                    "error": "This student is already verified. Please login."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        otp = generate_otp()

        try:

            with transaction.atomic():

                # Remove previous OTP

                EmailOTP.objects.filter(
                    user=user
                ).delete()

                # Create new OTP

                EmailOTP.objects.create(
                    user=user,
                    otp=otp,
                    expires_at=(
                        timezone.now() + timedelta(minutes=5)
                    )
                )

                # Send new OTP

                email_sent = send_student_otp(
                    user,
                    profile.name,
                    otp
                )

                if email_sent != 1:
                    raise RuntimeError("OTP email could not be sent")

        except Exception:

            logger.exception("OTP resend failed")

            return Response(
                {
                    "error": "Unable to send OTP. Please try again later."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "success": True,
                "message": "A new OTP has been sent successfully.",
                "student_no": profile.student_no
            },
            status=status.HTTP_200_OK
        )


# --------------------------------------------------
# PASSWORDLESS LOGIN - SEND OTP
# --------------------------------------------------

class LoginView(APIView):

    def post(self, request):

        student_no = (
            request.data.get("student_no") or ""
        ).strip()

        if not student_no:

            return Response(
                {
                    "error": "Student number is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            profile = StudentProfile.objects.select_related(
                "user"
            ).get(
                student_no=student_no
            )

        except StudentProfile.DoesNotExist:

            return Response(
                {
                    "error": "Student account not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user = profile.user

        if not user.is_active or not profile.is_email_verified:

            return Response(
                {
                    "error": "Please verify your email before logging in."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        otp = generate_otp()

        try:

            with transaction.atomic():

                # Delete previous login OTP

                EmailOTP.objects.filter(
                    user=user
                ).delete()

                # Generate new login OTP

                EmailOTP.objects.create(
                    user=user,
                    otp=otp,
                    expires_at=(
                        timezone.now() + timedelta(minutes=5)
                    )
                )

                email_sent = send_student_otp(
                    user,
                    profile.name,
                    otp
                )

                if email_sent != 1:
                    raise RuntimeError("Login OTP email could not be sent")

        except Exception:

            logger.exception("Login OTP sending failed")

            return Response(
                {
                    "error": "Unable to send login OTP. Please try again."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "success": True,
                "message": "Login OTP sent to your registered email.",
                "student_no": profile.student_no
            },
            status=status.HTTP_200_OK
        )


# --------------------------------------------------
# PASSWORDLESS LOGIN - VERIFY OTP
# --------------------------------------------------

class VerifyLoginOTPView(APIView):

    def post(self, request):

        student_no = (
            request.data.get("student_no") or ""
        ).strip()

        email = (
            request.data.get("email") or ""
        ).strip().lower()

        otp = (
            request.data.get("otp") or ""
        ).strip()

        if not student_no or not email or not otp:

            return Response(
                {
                    "error": "Student number, email and OTP are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            profile = StudentProfile.objects.select_related(
                "user"
            ).get(
                student_no=student_no,
                user__email__iexact=email
            )

        except StudentProfile.DoesNotExist:

            return Response(
                {
                    "error": "Invalid student details."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user = profile.user

        if not user.is_active or not profile.is_email_verified:

            return Response(
                {
                    "error": "Please verify your email before logging in."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():

            otp_record = EmailOTP.objects.select_for_update().filter(
                user=user
            ).order_by("-created_at").first()

            if otp_record is None:

                return Response(
                    {
                        "error": "OTP not found. Please request a new OTP."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if otp_record.expires_at < timezone.now():

                return Response(
                    {
                        "error": "OTP has expired. Please request a new OTP."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not secrets.compare_digest(
                str(otp_record.otp),
                otp
            ):

                return Response(
                    {
                        "error": "Incorrect OTP."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # OTP is valid. Delete it to prevent reuse.

            EmailOTP.objects.filter(
                user=user
            ).delete()

            # Generate authentication token

            token, created = Token.objects.get_or_create(
                user=user
            )

        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "name": profile.name,
                "email": user.email,
                "student_no": profile.student_no,
                "token": token.key
            },
            status=status.HTTP_200_OK
        )
class SuperuserLoginView(APIView):

    def post(self, request):

        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        if not username or not password:
            return Response(
                {"error": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(
            username=username,
            password=password
        )

        if (
            user is None
            or not user.is_active
            or not user.is_superuser
        ):
            return Response(
                {"error": "Invalid superuser credentials."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "message": "Superuser login successful.",
                "username": user.username,
                "token": token.key
            },
            status=status.HTTP_200_OK
        )

class DeleteRegistrationView(APIView):

    permission_classes = [IsSuperUser]

    def delete(self, request):

        student_no = request.data.get("student_no")

        # Check student number
        if not student_no:
            return Response(
                {
                    "success": False,
                    "message": "Student number is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find student registration
        try:
            student = StudentProfile.objects.select_related(
                "user"
            ).get(student_no=student_no)

        except StudentProfile.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Registration not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user = student.user

        # Protect admin accounts
        if user.is_superuser or user.is_staff:
            return Response(
                {
                    "success": False,
                    "message": "Admin accounts cannot be deleted."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Save details before deletion
        student_name = student.name
        registration_id = student.student_no
        student_email = user.email

        try:
            with transaction.atomic():

                # Delete account.
                # Student profile and related QR/attendance
                # records will follow their model's FK rules.
                user.delete()

            return Response(
                {
                    "success": True,
                    "message": "Registration deleted successfully.",
                    "deleted_student": {
                        "name": student_name,
                        "student_no": registration_id,
                        "email": student_email
                    }
                },
                status=status.HTTP_200_OK
            )

        except ProtectedError:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Cannot delete registration because "
                        "protected related records exist."
                    )
                },
                status=status.HTTP_409_CONFLICT
            )

        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred while deleting registration."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
