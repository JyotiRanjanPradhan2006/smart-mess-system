"""
accounts/models.py — FIXED: QR stores full student data as JSON
"""

import uuid
import json
import qrcode
import os
from io import BytesIO
from django.core.files import File
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        STAFF   = 'staff',   'Mess Staff'
        ADMIN   = 'admin',   'Admin'

    role  = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=15, blank=True)

    def is_student(self):      return self.role == self.Role.STUDENT
    def is_mess_staff(self):   return self.role == self.Role.STAFF
    def is_admin_user(self):   return self.role == self.Role.ADMIN or self.is_staff

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class StudentProfile(models.Model):
    class RegistrationStatus(models.TextChoices):
        PENDING  = 'pending',  'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    class CardStatus(models.TextChoices):
        ACTIVE  = 'active',  'Active'
        BLOCKED = 'blocked', 'Blocked'

    user                = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_number         = models.CharField(max_length=20, unique=True)
    department          = models.CharField(max_length=100, blank=True)
    year_of_study       = models.PositiveSmallIntegerField(null=True, blank=True)
    registration_status = models.CharField(max_length=10, choices=RegistrationStatus.choices, default=RegistrationStatus.PENDING)
    card_status         = models.CharField(max_length=10, choices=CardStatus.choices, default=CardStatus.ACTIVE)

    qr_code   = models.ImageField(upload_to='qr_codes/', blank=True)
    qr_token  = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    pending_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Student Profile'

    def __str__(self):
        return f"{self.user.get_full_name()} – {self.roll_number}"

    def get_pending_limit(self):
        return SystemConfig.get_solo().pending_limit

    def pending_fraction(self):
        limit = self.get_pending_limit()
        return float(self.pending_amount) / float(limit) if limit else 0

    def is_warning_threshold_reached(self):
        return self.pending_fraction() >= SystemConfig.get_solo().warning_fraction

    def is_over_limit(self):
        return self.pending_amount > self.get_pending_limit()

    def check_and_update_card_status(self):
        from billing.services import cancel_future_bookings_for_student
        from notifications.services import send_notification
        if self.is_over_limit():
            if self.card_status != self.CardStatus.BLOCKED:
                self.card_status = self.CardStatus.BLOCKED
                self.save(update_fields=['card_status'])
                cancel_future_bookings_for_student(self)
                send_notification(
                    student=self, notif_type='card_blocked',
                    message=(
                        f"Your mess card has been BLOCKED. "
                        f"Pending ₹{self.pending_amount} exceeds limit ₹{self.get_pending_limit()}."
                    ),
                )
        elif self.card_status == self.CardStatus.BLOCKED and not self.is_over_limit():
            self.card_status = self.CardStatus.ACTIVE
            self.save(update_fields=['card_status'])

    def get_qr_data(self):
        """
        Build the JSON payload stored INSIDE the QR code.
        Contains token + all student identity info.
        """
        return json.dumps({
            "token":      str(self.qr_token),
            "name":       self.user.get_full_name() or self.user.username,
            "roll":       self.roll_number,
            "dept":       self.department or "",
            "year":       self.year_of_study or "",
            "username":   self.user.username,
            "phone":      self.user.phone or "",
            "system":     "SmartMess",
        }, separators=(',', ':'))

    def generate_qr(self):
        """Generate QR with full student data encoded inside."""
        qr_data = self.get_qr_data()
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=3,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f"qr_{self.roll_number}.png"
        self.qr_code.save(filename, File(buffer), save=False)

    def regenerate_qr(self):
        """Force regenerate QR (call after profile update)."""
        if self.qr_code:
            try:
                os.remove(self.qr_code.path)
            except Exception:
                pass
            self.qr_code = None
        self.generate_qr()
        self.save(update_fields=['qr_code'])

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr()
        super().save(*args, **kwargs)


class SystemConfig(models.Model):
    pending_limit           = models.DecimalField(max_digits=10, decimal_places=2, default=3000)
    warning_fraction        = models.FloatField(default=2/3)
    booking_deadline_hour   = models.PositiveSmallIntegerField(default=9)
    booking_deadline_minute = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name        = 'System Configuration'
        verbose_name_plural = 'System Configuration'

    def __str__(self):
        return "System Configuration"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def booking_deadline_passed(self):
        now = timezone.localtime(timezone.now())
        deadline = now.replace(
            hour=self.booking_deadline_hour,
            minute=self.booking_deadline_minute,
            second=0, microsecond=0,
        )
        return now >= deadline