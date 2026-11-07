
import secrets
from io import BytesIO
from email.mime.image import MIMEImage

import qrcode

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import escape

from .models import StudentQR


def create_student_qr(student):
    student_qr, created = StudentQR.objects.get_or_create(
        student=student,
        defaults={
            "qr_token": secrets.token_urlsafe(32)
        }
    )
    return student_qr


def generate_qr_image(student_qr):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

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


def send_student_qr_email(student):
    student_qr = create_student_qr(student)
    qr_image = generate_qr_image(student_qr)

    recipient_email = student.user.email

    student_name = escape(student.name)
    student_number = escape(student.student_no)

    subject = "Your AWS Event Student QR Pass"

    text_content = f"""
Hello {student.name},

Your email has been verified successfully.
Your student account is now active.

Your permanent QR pass is included in this email.

Student Name: {student.name}
Student Number: {student.student_no}

Keep your QR code safe. Use the same permanent QR code
for attendance at future AWS events.

AWS Event | Student Event Management System
"""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>

    <body style="
        margin: 0;
        padding: 20px;
        background-color: #111111;
        font-family: Arial, Helvetica, sans-serif;
    ">

        <div style="
            max-width: 600px;
            margin: auto;
            background-color: #202124;
            border-radius: 16px;
            overflow: hidden;
            color: #ffffff;
        ">

            <div style="
                background-color: #e8eafe;
                padding: 35px 20px;
                text-align: center;
                color: #202124;
            ">
                <h1 style="
                    margin: 0;
                    font-size: 32px;
                    letter-spacing: 5px;
                ">AWS EVENT</h1>

                <p style="
                    margin: 15px 0 0;
                    font-size: 15px;
                    letter-spacing: 4px;
                ">STUDENT ACCESS PASS</p>
            </div>

            <div style="padding: 35px 30px;">

                <h1 style="
                    font-size: 30px;
                    line-height: 1.3;
                    margin-top: 0;
                ">
                    You're all set, {student_name}!
                </h1>

                <p style="
                    color: #aab7cf;
                    font-size: 17px;
                    line-height: 1.8;
                ">
                    Your email has been verified successfully.
                    Your student account is now active.
                </p>

                <div style="
                    margin: 30px 0;
                    padding: 25px 15px;
                    border: 1px solid #383d46;
                    border-radius: 16px;
                    text-align: center;
                ">

                    <p style="
                        color: #aab7cf;
                        letter-spacing: 3px;
                        font-size: 14px;
                    ">
                        YOUR PERMANENT QR PASS
                    </p>

                    <img
                        src="cid:student_qr"
                        alt="Your Student QR Code"
                        width="250"
                        style="
                            display: block;
                            width: 250px;
                            max-width: 100%;
                            height: auto;
                            margin: 20px auto;
                            background: #ffffff;
                            padding: 12px;
                            border-radius: 12px;
                        "
                    >

                    <p style="
                        color: #4caf67;
                        font-size: 16px;
                        font-weight: bold;
                    ">
                        &#10003; ACCOUNT VERIFIED
                    </p>
                </div>

                <div style="margin-top: 35px;">

                    <p style="
                        color: #8998b1;
                        font-size: 13px;
                        letter-spacing: 2px;
                    ">STUDENT NAME</p>

                    <h2 style="font-size: 21px;">
                        {student_name}
                    </h2>

                    <hr style="border: 0; border-top: 1px solid #383d46;">

                    <p style="
                        color: #8998b1;
                        font-size: 13px;
                        letter-spacing: 2px;
                    ">STUDENT NUMBER</p>

                    <h2 style="font-size: 21px;">
                        {student_number}
                    </h2>
                </div>

                <div style="
                    margin-top: 35px;
                    padding: 20px;
                    background-color: #e8eafe;
                    color: #202124;
                    border-radius: 12px;
                    text-align: center;
                    font-size: 17px;
                    font-weight: bold;
                ">
                    Your permanent QR pass is included above.
                </div>

                <p style="
                    color: #aab7cf;
                    font-size: 16px;
                    line-height: 1.8;
                    margin-top: 30px;
                ">
                    Keep your QR code safe. Use the same permanent
                    QR code for attendance at future AWS events.
                </p>

            </div>

            <div style="
                padding: 25px;
                text-align: center;
                background-color: #1c1d1f;
                color: #aab7cf;
            ">
                <p>AWS Event | Student Event Management System</p>

                <p style="font-size: 13px; color: #7d8798;">
                    This is an automated email. Please do not reply.
                </p>
            </div>

        </div>

    </body>
    </html>
    """

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )

    email.attach_alternative(html_content, "text/html")

    # Embed the QR image using a Content-ID.
    # The HTML image source must match this ID.
    image_part = MIMEImage(qr_image.getvalue(), _subtype="png")
    image_part.add_header("Content-ID", "<student_qr>")
    image_part.add_header(
        "Content-Disposition",
        "inline",
        filename="student_qr.png"
    )

    email.attach(image_part)

    email.send(fail_silently=False)

    return student_qr
