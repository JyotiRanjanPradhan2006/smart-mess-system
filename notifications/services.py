"""
notifications/services.py
Central service for creating & broadcasting notifications.
"""

from .models import Notification


def send_notification(student, notif_type, message):
    """Create a notification record for a single student."""
    Notification.objects.create(
        student=student,
        notif_type=notif_type,
        message=message,
    )


def broadcast_notification(notif_type, message, queryset=None):
    """
    Send same notification to all approved students (or a custom queryset).
    """
    from accounts.models import StudentProfile
    qs = queryset or StudentProfile.objects.filter(
        registration_status=StudentProfile.RegistrationStatus.APPROVED
    )
    objs = [
        Notification(student=s, notif_type=notif_type, message=message)
        for s in qs
    ]
    Notification.objects.bulk_create(objs)


def notify_menu_change(menu_config):
    msg = (
        f"📋 Menu Updated: {menu_config.get_meal_session_display()} on {menu_config.effective_date} "
        f"now offers: {'Veg' if menu_config.has_veg else ''} "
        f"{'& Non-Veg' if menu_config.has_nonveg else ''}. "
        f"Your affected bookings have been cancelled – please reschedule."
    )
    broadcast_notification(Notification.NotifType.MENU_CHANGE, msg)


def notify_price_change(meal_price):
    msg = (
        f"💰 Price Updated: {meal_price.get_meal_type_display()} "
        f"{meal_price.get_meal_session_display()} is now ₹{meal_price.price} "
        f"effective from {meal_price.effective_from}. "
        f"Your affected bookings have been cancelled – please reschedule."
    )
    broadcast_notification(Notification.NotifType.PRICE_CHANGE, msg)


def notify_pending_warning(student):
    msg = (
        f"⚠️ Your pending amount ₹{student.pending_amount} has crossed "
        f"the warning threshold. Please clear dues to avoid card blocking."
    )
    send_notification(student, Notification.NotifType.WARNING_PENDING, msg)
