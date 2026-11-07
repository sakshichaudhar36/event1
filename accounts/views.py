
import json
import logging
import secrets
import uuid
import urllib.parse
import urllib.request

from datetime import timedelta
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
import requests
from django.conf import settings
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
        print("CAPTCHA ERROR: Token is missing")
        return False

    secret = settings.RECAPTCHA_SECRET_KEY

    if not secret:
        print("CAPTCHA ERROR: Secret key is not loaded")
        return False

    try:
        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": secret,
                "response": captcha_token
            },
            timeout=10
        )

        result = response.json()
        print("CAPTCHA GOOGLE RESPONSE:", result)

        return result.get("success", False)

    except requests.RequestException as error:
        print("CAPTCHA REQUEST ERROR:", error)
        return False

# --------------------------------------------------
# OTP GENERATION
# --------------------------------------------------

def generate_otp():

   return str(secrets.randbelow(900000) + 100000)


# --------------------------------------------------
# SEND OTP EMAIL
# --------------------------------------------------

def send_student_otp(user, name, otp):

   send_mail(
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

       # 1. Verify Google reCAPTCHA first

       captcha_token = request.data.get(
           "g-recaptcha-response"
       )

       if not verify_recaptcha(captcha_token):

           return Response(
               {
                   "error": "CAPTCHA verification failed. Please try again."
               },
               status=status.HTTP_400_BAD_REQUEST
           )

       # 2. Validate registration data

       serializer = RegisterSerializer(
           data=request.data
       )

       if not serializer.is_valid():

           return Response(
               serializer.errors,
               status=status.HTTP_400_BAD_REQUEST
           )

       data = serializer.validated_data

       email = data["email"].strip().lower()

       otp = generate_otp()

       # 3. Generate unique internal username

       username_base = slugify(data["name"])[:140] or "student"

       username = (
           f"{username_base}_{uuid.uuid4().hex[:8]}"
       )

       # 4. Create student and send OTP

       try:

           with transaction.atomic():

               user = User.objects.create_user(
                   username=username,
                   email=email,
                   password=data["password"],
                   is_active=False
               )

               profile = StudentProfile.objects.create(
                   user=user,
                   name=data["name"],
                   section=data["section"],
                   year=data["year"],
                   residence=data["residence"],
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

               send_student_otp(
                   user,
                   profile.name,
                   otp
               )

       except Exception:

           logger.exception("Student registration failed")

           return Response(
               {
                   "error": "Registration failed. Please check your details and try again."
               },
               status=status.HTTP_500_INTERNAL_SERVER_ERROR
           )

       return Response(
           {
               "message": "Registration successful. OTP sent to your email.",
               "name": profile.name,
               "email": user.email,
               "student_no": profile.student_no
           },
           status=status.HTTP_201_CREATED
       )


# --------------------------------------------------
# VERIFY OTP API
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

       # Find the exact student, not just the Gmail address

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

       # Lock and verify the latest OTP

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

           # Activate student

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

           # Send permanent QR email after database commit

           transaction.on_commit(
               lambda: send_qr_email_safely(profile)
           )

       return Response(
           {
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

               # Remove old OTP

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

               send_student_otp(
                   user,
                   profile.name,
                   otp
               )

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
               "message": "A new OTP has been sent successfully.",
               "student_no": profile.student_no
           },
           status=status.HTTP_200_OK
       )


# --------------------------------------------------
# LOGIN API
# --------------------------------------------------

class LoginView(APIView):

   def post(self, request):

       student_no = (
           request.data.get("student_no") or ""
       ).strip()

       password = request.data.get("password") or ""

       if not student_no or not password:

           return Response(
               {
                   "error": "Student number and password are required."
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
                   "error": "Invalid student number or password."
               },
               status=status.HTTP_401_UNAUTHORIZED
           )

       user = authenticate(
           username=profile.user.username,
           password=password
       )

       if user is None:

           return Response(
               {
                   "error": "Invalid student number or password."
               },
               status=status.HTTP_401_UNAUTHORIZED
           )

       if not user.is_active or not profile.is_email_verified:

           return Response(
               {
                   "error": "Please verify your email before logging in."
               },
               status=status.HTTP_403_FORBIDDEN
           )

       token, created = Token.objects.get_or_create(
           user=user
       )

       return Response(
           {
               "message": "Login successful.",
               "name": profile.name,
               "email": user.email,
               "student_no": profile.student_no,
               "token": token.key
           },
           status=status.HTTP_200_OK
       )

