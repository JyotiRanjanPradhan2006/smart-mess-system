"""
attendance/models.py — ForeignKey allows multiple logs per booking
"""

from django.db import models


class AttendanceLog(models.Model):

    class ScanResult(models.TextChoices):
        VALID         = 'valid',         'Valid – Attendance Marked'
        INVALID_QR    = 'invalid_qr',    'Invalid QR Token'
        NOT_BOOKED    = 'not_booked',    'No Booking Found'
        CARD_BLOCKED  = 'card_blocked',  'Card Blocked'
        ALREADY_USED  = 'already_used',  'Already Attended'
        NOT_APPROVED  = 'not_approved',  'Student Not Approved'

    booking     = models.ForeignKey(
        'meals.DailyBooking', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='attendance_logs'
    )
    qr_token    = models.UUIDField(help_text="Token scanned from QR code")
    scan_result = models.CharField(max_length=20, choices=ScanResult.choices)
    scanned_by  = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='scans_performed'
    )
    scanned_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scanned_at']
        verbose_name = 'Attendance Log'

    def __str__(self):
        return f"{self.scan_result} | {self.scanned_at:%Y-%m-%d %H:%M}"