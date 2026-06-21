"""
billing/services.py
Business logic for booking cancellation, billing recalculation,
and menu/price invalidation workflows.
"""

from django.utils import timezone
from meals.models import DailyBooking, MealPrice
from notifications.services import send_notification
from notifications.models import Notification


def cancel_future_bookings_for_student(student_profile, reason='card_blocked'):
    """Cancel all future BOOKED entries for a student."""
    today = timezone.localdate()
    qs = DailyBooking.objects.filter(
        student=student_profile,
        date__gte=today,
        status=DailyBooking.BookingStatus.BOOKED,
    )
    count = qs.count()
    qs.update(status=DailyBooking.BookingStatus.CANCELLED)
    return count


def invalidate_schedules_and_bookings(trigger='menu'):
    """
    Called when Admin changes menu or prices.
    1. Deactivate all active WeeklySchedules.
    2. Cancel all future bookings.
    3. Notify all students.
    """
    from meals.models import WeeklySchedule
    from accounts.models import StudentProfile

    today = timezone.localdate()

    # Cancel future bookings
    DailyBooking.objects.filter(
        date__gte=today,
        status=DailyBooking.BookingStatus.BOOKED,
    ).update(status=DailyBooking.BookingStatus.CANCELLED)

    # Deactivate weekly schedules
    WeeklySchedule.objects.filter(is_active=True).update(is_active=False)

    # Notify all approved students
    notif_type = (
        Notification.NotifType.MENU_CHANGE if trigger == 'menu'
        else Notification.NotifType.PRICE_CHANGE
    )
    msg = (
        "Your weekly schedule has been reset and future bookings cancelled "
        "due to a menu/price update by admin. Please set a new weekly schedule."
    )
    students = StudentProfile.objects.filter(
        registration_status=StudentProfile.RegistrationStatus.APPROVED
    )
    from notifications.services import broadcast_notification
    broadcast_notification(notif_type, msg, queryset=students)


def recalculate_student_bill(student_profile, year=None, month=None):
    """Regenerate MonthlyBill for a student and update pending amount."""
    from billing.models import MonthlyBill
    from django.db.models import Sum

    now = timezone.localdate()
    year  = year  or now.year
    month = month or now.month

    bill, _ = MonthlyBill.objects.get_or_create(
        student=student_profile, year=year, month=month
    )
    bill.recalculate()

    # Recompute pending
    total_billed = MonthlyBill.objects.filter(
        student=student_profile
    ).aggregate(s=Sum('total_amount'))['s'] or 0

    from billing.models import Payment
    total_paid = Payment.objects.filter(
        student=student_profile
    ).aggregate(s=Sum('amount'))['s'] or 0

    student_profile.pending_amount = max(total_billed - total_paid, 0)
    student_profile.save(update_fields=['pending_amount'])

    # Threshold checks
    if student_profile.is_warning_threshold_reached() and not student_profile.is_over_limit():
        send_notification(
            student=student_profile,
            notif_type=Notification.NotifType.WARNING_PENDING,
            message=(
                f"⚠️ Pending amount ₹{student_profile.pending_amount} "
                f"has crossed the warning level. Please clear dues soon."
            ),
        )

    student_profile.check_and_update_card_status()
    return bill
