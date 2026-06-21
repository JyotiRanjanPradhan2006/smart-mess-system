"""
notifications/models.py
"""

from django.db import models
from django.conf import settings


class Notification(models.Model):

    class NotifType(models.TextChoices):
        MENU_CHANGE        = 'menu_change',        'Menu Changed'
        PRICE_CHANGE       = 'price_change',       'Price Changed'
        BOOKING_CANCELLED  = 'booking_cancelled',  'Booking Cancelled'
        WARNING_PENDING    = 'warning_pending',    'Pending Amount Warning'
        CARD_BLOCKED       = 'card_blocked',       'Card Blocked'
        CARD_UNBLOCKED     = 'card_unblocked',     'Card Unblocked'
        GENERAL            = 'general',            'General'
        REGISTRATION       = 'registration',       'Registration Update'

    student    = models.ForeignKey(
        'accounts.StudentProfile', on_delete=models.CASCADE, related_name='notifications'
    )
    notif_type = models.CharField(max_length=20, choices=NotifType.choices, default=NotifType.GENERAL)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'

    def __str__(self):
        return f"[{self.get_notif_type_display()}] → {self.student} | {self.created_at:%Y-%m-%d %H:%M}"

    @classmethod
    def mark_all_read(cls, student):
        cls.objects.filter(student=student, is_read=False).update(is_read=True)
