"""attendance/admin.py"""
from django.contrib import admin
from .models import AttendanceLog


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = ('scanned_at', 'scan_result', 'booking', 'scanned_by')
    list_filter  = ('scan_result',)
    date_hierarchy = 'scanned_at'
    readonly_fields = ('qr_token', 'scanned_at')
