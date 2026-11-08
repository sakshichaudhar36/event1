
import secrets
from io import BytesIO
from email.mime.image import MIMEImage

import qrcode

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import escape

from .models import StudentQR


# ==================================================
# CREATE OR GET PERMANENT STUDENT QR
# ==================================================

def create_student_qr(student):
    student_qr, created = StudentQR.objects.get_or_create(
        student=student,
        defaults={
            "qr_token": secrets.token_urlsafe(32)
        }
    )

    return student_qr


# ==================================================
# GENERATE QR IMAGE
# ==================================================

def generate_qr_image(student_qr):

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    # IMPORTANT: QR contains unique token
    # It does NOT contain the student number.
    qr.add_data(student_qr.qr_token)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    image_buffer = BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    return image_buffer


# ==================================================
# SEND CLOUD CLASH CONFIRMATION EMAIL
# ==================================================

def send_student_qr_email(student):

    # 1. Get permanent QR
    student_qr = create_student_qr(student)

    # 2. Generate QR image
    qr_image = generate_qr_image(student_qr)

    # 3. Student details
    recipient_email = student.user.email

    student_name = escape(student.name)
    student_number = escape(student.student_no)

    # 4. Event details
    event_date = "18/11/2026"
    event_time = "11:00 AM - 1:00 PM"
    event_venue = "CS-IT Seminar Hall"

    # 5. Email subject
    subject = (
        "Registration Confirmed | "
        "Cloud Clash - AWS Builder Group"
    )

    # ==================================================
    # PLAIN TEXT EMAIL
    # ==================================================

    text_content = f"""
AWS BUILDER GROUP PRESENTS

CLOUD CLASH
THE ULTIMATE CLOUD EXPERIENCE

YOUR CLOUD JOURNEY STARTS HERE.

REGISTRATION CONFIRMED!

Hey, {student.name}!

Get ready to clash, compete, collaborate and explore
the world of cloud computing!

YOUR ENTRY PASS

Your permanent QR code is included in this email.

Student Name: {student.name}

Unique Registration ID: {student.student_no}

EVENT DETAILS

Date: {event_date}
Time: {event_time}
Venue: {event_venue}

IMPORTANT:

Keep your QR code handy. It is your official entry pass.
Present it at the entrance for verification.

LET THE CLASH BEGIN!

See you at Cloud Clash!

Team AWS Builder Group

POWERED BY AWS BUILDER GROUP
"""

    # ==================================================
    # HTML EMAIL DESIGN
    # ==================================================

    html_content = f"""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>Cloud Clash Registration Confirmed</title>
</head>

<body style="
    margin:0;
    padding:20px 10px;
    background-color:#eeeeee;
    font-family:Arial,Helvetica,sans-serif;
    color:#171717;
">

<table width="100%"
       cellpadding="0"
       cellspacing="0"
       border="0"
       style="
            max-width:600px;
            margin:auto;
            background:#ffffff;
            border-radius:18px;
            overflow:hidden;
       ">

    <!-- HEADER -->

    <tr>
        <td align="center"
            style="
                background:#111111;
                padding:35px 20px;
            ">

            <p style="
                margin:0 0 15px;
                color:#F97316;
                font-size:18px;
                font-weight:bold;
                letter-spacing:1px;
            ">
                AWS BUILDER GROUP PRESENTS
            </p>

            <h1 style="
                margin:0;
                color:#FFCC00;
                font-size:43px;
                font-weight:900;
                letter-spacing:1px;
            ">
                CLOUD CLASH
            </h1>

            <p style="
                color:#ffffff;
                font-size:17px;
                font-weight:bold;
                margin:18px 0 0;
            ">
                THE ULTIMATE CLOUD EXPERIENCE
            </p>

            <div style="
                width:90px;
                height:6px;
                background:#FFCC00;
                margin:22px auto;
            "></div>

            <p style="
                color:#ffffff;
                font-size:16px;
                margin:0;
            ">
                YOUR CLOUD JOURNEY STARTS HERE.
            </p>

        </td>
    </tr>

    <!-- REGISTRATION CONFIRMATION -->

    <tr>
        <td align="center"
            style="
                background:#FFCC00;
                padding:28px 20px;
            ">

            <div style="
                font-size:43px;
                color:#111111;
                font-weight:bold;
            ">
                &#10004;
            </div>

            <h1 style="
                margin:12px 0;
                color:#111111;
                font-size:30px;
                line-height:1.3;
            ">
                REGISTRATION<br>
                CONFIRMED!
            </h1>

            <p style="
                margin:0;
                color:#222222;
                font-size:18px;
                font-weight:bold;
            ">
                You're officially in the game.
            </p>

        </td>
    </tr>

    <!-- MAIN CONTENT -->

    <tr>
        <td style="padding:28px 22px;">

            <h1 style="
                margin:0 0 15px;
                font-size:30px;
                color:#171717;
            ">
                Hey, {student_name}!
            </h1>

            <p style="
                font-size:17px;
                line-height:1.7;
                color:#444444;
                margin:0 0 25px;
            ">
                Get ready to clash, compete, collaborate
                and explore the world of cloud computing!
            </p>

            <!-- ENTRY PASS -->

            <table width="100%"
                   cellpadding="0"
                   cellspacing="0"
                   style="
                        background:#171717;
                        border-radius:20px;
                        overflow:hidden;
                   ">

                <tr>
                    <td align="center"
                        style="padding:28px 15px;">

                        <h1 style="
                            margin:0 0 15px;
                            color:#FFCC00;
                            font-size:30px;
                        ">
                            YOUR ENTRY PASS
                        </h1>

                        <p style="
                            color:#ffffff;
                            font-size:16px;
                            margin:0 0 20px;
                        ">
                            SCAN TO ENTER CLOUD CLASH
                        </p>

                        <!-- QR CODE -->

                        <img
                            src="cid:student_qr"
                            alt="Cloud Clash Entry QR Code"
                            width="230"
                            style="
                                display:block;
                                width:230px;
                                max-width:100%;
                                height:auto;
                                padding:12px;
                                margin:0 auto 18px;
                                background:#ffffff;
                                border-radius:12px;
                                box-sizing:border-box;
                            "
                        >

                        <p style="
                            margin:0 0 8px;
                            color:#FFCC00;
                            font-size:15px;
                            font-weight:bold;
                        ">
                            UNIQUE REGISTRATION ID
                        </p>

                        <p style="
                            margin:0;
                            color:#ffffff;
                            font-size:19px;
                            font-weight:bold;
                            letter-spacing:1px;
                        ">
                            {student_number}
                        </p>

                    </td>
                </tr>

            </table>

            <!-- EVENT DETAILS -->

            <h2 style="
                margin:32px 0 20px;
                color:#171717;
                font-size:25px;
            ">
                EVENT DETAILS
            </h2>

            <table width="100%"
                   cellpadding="0"
                   cellspacing="0">

                <tr>
                    <td style="
                        padding:10px 0;
                        font-size:16px;
                        color:#444444;
                    ">
                        <span style="color:#B8860B;">
                            &#128197;
                        </span>
                        &nbsp; Date: {event_date}
                    </td>
                </tr>

                <tr>
                    <td style="
                        padding:10px 0;
                        font-size:16px;
                        color:#444444;
                    ">
                        <span style="color:#B8860B;">
                            &#128337;
                        </span>
                        &nbsp; Time: {event_time}
                    </td>
                </tr>

                <tr>
                    <td style="
                        padding:10px 0;
                        font-size:16px;
                        color:#444444;
                    ">
                        <span style="color:#B8860B;">
                            &#128205;
                        </span>
                        &nbsp; Venue: {event_venue}
                    </td>
                </tr>

            </table>

            <!-- IMPORTANT NOTICE -->

            <table width="100%"
                   cellpadding="0"
                   cellspacing="0"
                   style="
                        margin-top:22px;
                        background:#FFF4CC;
                        border-radius:15px;
                   ">

                <tr>
                    <td style="padding:20px;">

                        <h2 style="
                            margin:0 0 12px;
                            color:#171717;
                            font-size:22px;
                        ">
                            IMPORTANT
                        </h2>

                        <p style="
                            margin:0;
                            color:#444444;
                            font-size:16px;
                            line-height:1.7;
                        ">
                            Keep your QR code handy.
                            It is your official entry pass.
                            Present it at the entrance
                            for verification.
                        </p>

                    </td>
                </tr>

            </table>

            <!-- CLOSING MESSAGE -->

            <h2 style="
                margin:32px 0 12px;
                font-size:27px;
                color:#171717;
            ">
                LET THE CLASH BEGIN!
            </h2>

            <p style="
                color:#444444;
                font-size:17px;
                line-height:1.6;
            ">
                See you at Cloud Clash!
            </p>

            <h3 style="
                color:#171717;
                font-size:20px;
                margin-top:25px;
            ">
                Team AWS Builder Group
            </h3>

        </td>
    </tr>

    <!-- FOOTER -->

    <tr>
        <td align="center"
            style="
                background:#111111;
                padding:28px 15px;
            ">

            <h1 style="
                margin:0 0 10px;
                color:#FFCC00;
                font-size:28px;
            ">
                CLOUD CLASH
            </h1>

            <p style="
                margin:0;
                color:#ffffff;
                font-size:16px;
            ">
                POWERED BY AWS BUILDER GROUP
            </p>

            <p style="
                margin:18px 0 0;
                color:#999999;
                font-size:12px;
            ">
                This is an automated email.
                Please do not reply.
            </p>

        </td>
    </tr>

</table>

</body>
</html>
"""

    # ==================================================
    # CREATE EMAIL
    # ==================================================

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )

    email.attach_alternative(
        html_content,
        "text/html"
    )

    # ==================================================
    # EMBED QR IMAGE
    # ==================================================

    qr_image.seek(0)

    image_part = MIMEImage(
        qr_image.read(),
        _subtype="png"
    )

    image_part.add_header(
        "Content-ID",
        "<student_qr>"
    )

    image_part.add_header(
        "Content-Disposition",
        "inline",
        filename="cloud_clash_entry_pass.png"
    )

    email.attach(image_part)

    # ==================================================
    # SEND EMAIL
    # ==================================================

    email.send(fail_silently=False)

    return student_qr
