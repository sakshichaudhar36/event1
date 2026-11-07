
from django.urls import path

from .views import (
    QRAttendanceView,
    ManualAttendanceView,
    AttendanceListView,
    AttendanceSummaryView,
)

urlpatterns = [
    path(
        "qr-attendance/",
        QRAttendanceView.as_view(),
        name="qr-attendance"
    ),

    path(
        "manual-attendance/",
        ManualAttendanceView.as_view(),
        name="manual-attendance"
    ),

    path(
        "attendance/",
        AttendanceListView.as_view(),
        name="attendance-list"
    ),

    path(
        "summary/",
        AttendanceSummaryView.as_view(),
        name="attendance-summary"
    ),
]
