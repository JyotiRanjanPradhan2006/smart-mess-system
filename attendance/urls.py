"""attendance/urls.py"""
from django.urls import path
from . import views

urlpatterns = [
    path('scan/',    views.scan_qr_view,          name='scan_qr'),
    path('process/', views.process_scan_api,       name='process_scan'),
    path('report/',  views.attendance_report_view, name='attendance_report'),
]
