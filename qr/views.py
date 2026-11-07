from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse

from .models import StudentQR
from .services import generate_qr_image


class MyQRCodeView(APIView):
    permission_classes = [IsAuthenticated]

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