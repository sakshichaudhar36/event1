from django.urls import path
from .views import MyQRCodeView

urlpatterns = [
    path("my-qr/", MyQRCodeView.as_view(), name="my-qr"),
]