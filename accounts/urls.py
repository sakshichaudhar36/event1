from django.urls import path
from .views import (
    RegisterView,
    VerifyOTPView,
    ResendOTPView,
    LoginView,
    VerifyLoginOTPView,
    SuperuserLoginView,
    DeleteRegistrationView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),

    path("verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),

    path("resend-otp/", ResendOTPView.as_view(), name="resend_otp"),

    path("login/", LoginView.as_view(), name="login"),

    path(
        "verify-login-otp/",
        VerifyLoginOTPView.as_view(),
        name="verify_login_otp",
    ),
    path(
    "delete-registration/",
    DeleteRegistrationView.as_view(),
    name="delete_registration"),

    path(
        "admin-login/",
        SuperuserLoginView.as_view(),
        name="admin_login",
    ),
]