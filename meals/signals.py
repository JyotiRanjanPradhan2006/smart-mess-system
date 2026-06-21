"""
meals/signals.py
Trigger schedule invalidation when Admin saves a MenuConfig or MealPrice.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='meals.MenuConfig')
def on_menu_change(sender, instance, created, **kwargs):
    if not created:  # Only on updates
        from billing.services import invalidate_schedules_and_bookings
        invalidate_schedules_and_bookings(trigger='menu')


@receiver(post_save, sender='meals.MealPrice')
def on_price_change(sender, instance, created, **kwargs):
    from billing.services import invalidate_schedules_and_bookings
    invalidate_schedules_and_bookings(trigger='price')


@receiver(post_save, sender='accounts.StudentProfile')
def on_student_approved(sender, instance, **kwargs):
    """Notify student when registration status changes."""
    if instance.registration_status == instance.RegistrationStatus.APPROVED:
        from notifications.services import send_notification
        send_notification(
            student=instance,
            notif_type='registration',
            message="🎉 Your registration has been approved! You can now set your weekly meal schedule.",
        )
