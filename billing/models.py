"""
billing/models.py
Monthly bill summary + payment records.
"""

from django.db import models
from django.utils import timezone


class MonthlyBill(models.Model):
    """Aggregated billing record per student per month."""

    student       = models.ForeignKey(
        'accounts.StudentProfile', on_delete=models.CASCADE, related_name='monthly_bills'
    )
    year          = models.PositiveIntegerField()
    month         = models.PositiveSmallIntegerField()  # 1-12
    total_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_finalised  = models.BooleanField(default=False)
    generated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'year', 'month')
        ordering = ['-year', '-month']
        verbose_name = 'Monthly Bill'

    def __str__(self):
        return f"{self.student} – {self.year}/{self.month:02d} – ₹{self.total_amount}"

    def recalculate(self):
        """Sum all billable bookings for this student-month."""
        from meals.models import DailyBooking
        import datetime
        bookings = DailyBooking.objects.filter(
            student=self.student,
            date__year=self.year,
            date__month=self.month,
        ).exclude(status='cancelled').exclude(meal_type='skip')
        self.total_amount = sum(b.price_snapshot for b in bookings)
        self.save(update_fields=['total_amount', 'generated_at'])
        return self.total_amount


class Payment(models.Model):
    """A payment made by a student (manually recorded by admin)."""

    class PaymentMode(models.TextChoices):
        CASH   = 'cash',   'Cash'
        ONLINE = 'online', 'Online Transfer'
        UPI    = 'upi',    'UPI'
        OTHER  = 'other',  'Other'

    student      = models.ForeignKey(
        'accounts.StudentProfile', on_delete=models.CASCADE, related_name='payments'
    )
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    mode         = models.CharField(max_length=10, choices=PaymentMode.choices, default=PaymentMode.CASH)
    reference_no = models.CharField(max_length=50, blank=True)
    notes        = models.TextField(blank=True)
    recorded_by  = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='recorded_payments'
    )
    paid_at      = models.DateTimeField(default=timezone.now)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_at']
        verbose_name = 'Payment'

    def __str__(self):
        return f"{self.student} – ₹{self.amount} ({self.get_mode_display()}) on {self.paid_at:%Y-%m-%d}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update student financials
        profile = self.student
        from django.db.models import Sum
        total_paid = Payment.objects.filter(student=profile).aggregate(s=Sum('amount'))['s'] or 0
        total_billed = sum(
            b.total_amount for b in profile.monthly_bills.all()
        )
        profile.paid_amount = total_paid
        profile.pending_amount = max(total_billed - total_paid, 0)
        profile.save(update_fields=['paid_amount', 'pending_amount'])
        profile.check_and_update_card_status()
