from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from django.http import HttpResponse

from .models import StudentQR
from .services import generate_qr_image
from accounts.throttles import QRThrottle


class MyQRCodeView(APIView):
    permission_classes = [IsAuthenticated]

    throttle_classes = [
        UserRateThrottle,
        QRThrottle,
    ]

    def get(self, request):

        try:
            student_qr = StudentQR.objects.get(
                student__user=request.user
            )

        except StudentQR.DoesNotExist:
            return Response(
                {"error": "QR code not found."},
                status=404
            )

        qr_image = generate_qr_image(student_qr)

        response = HttpResponse(
            qr_image.getvalue(),
            content_type="image/png"
        )

        response["Content-Disposition"] = (
            'inline; filename="student_qr.png"'
        )

        return response