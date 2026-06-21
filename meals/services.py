"""
meals/services.py — FIXED (update_or_create, no IndentationError)
"""

import datetime
from django.utils import timezone
from .models import WeeklySchedule, DailyBooking, MealPrice, MenuConfig, MealType


def generate_bookings_from_schedule(schedule: WeeklySchedule, weeks_ahead: int = 4):
    """
    Delete all future BOOKED bookings for student, then create fresh ones.
    Uses update_or_create to safely handle any attended/missed rows.
    """
    today   = timezone.localdate()
    student = schedule.student

    # Cancel future booked bookings cleanly
    DailyBooking.objects.filter(
        student=student,
        date__gte=today,
        status=DailyBooking.BookingStatus.BOOKED,
    ).delete()

    created = []

    for week_offset in range(weeks_ahead):
        week_start = schedule.week_start + datetime.timedelta(weeks=week_offset)

        for item in schedule.items.all():
            booking_date = week_start + datetime.timedelta(days=item.day_of_week)

            if booking_date < today:
                continue
            if item.meal_preference == MealType.SKIP:
                continue

            # Validate against current menu
            menu = MenuConfig.get_for_date(booking_date, item.meal_session)
            if menu and item.meal_preference not in menu.allowed_choices():
                continue

            price = MealPrice.get_price_for(
                item.meal_preference, item.meal_session, booking_date
            )

            booking, _ = DailyBooking.objects.update_or_create(
                student=student,
                date=booking_date,
                meal_session=item.meal_session,
                defaults={
                    'meal_type':      item.meal_preference,
                    'price_snapshot': price,
                    'source':         DailyBooking.BookingSource.AUTO,
                    'status':         DailyBooking.BookingStatus.BOOKED,
                }
            )
            created.append(booking)

    return created


def override_daily_booking(student_profile, date, session, new_meal_type):
    """Student manually overrides a single day booking."""
    from accounts.models import SystemConfig
    cfg   = SystemConfig.get_solo()
    today = timezone.localdate()

    if date < today:
        return None, "Cannot change past bookings."
    if date == today and cfg.booking_deadline_passed():
        return None, f"Booking deadline ({cfg.booking_deadline_hour:02d}:{cfg.booking_deadline_minute:02d}) has passed."
    if student_profile.card_status == student_profile.CardStatus.BLOCKED:
        return None, "Your mess card is blocked. Please clear pending dues."

    menu = MenuConfig.get_for_date(date, session)
    if menu and new_meal_type not in menu.allowed_choices():
        return None, f"'{new_meal_type}' is not available on {date} for {session}."

    price = 0
    if new_meal_type != MealType.SKIP:
        price = MealPrice.get_price_for(new_meal_type, session, date)

    booking, _ = DailyBooking.objects.update_or_create(
        student=student_profile,
        date=date,
        meal_session=session,
        defaults={
            'meal_type':      new_meal_type,
            'price_snapshot': price,
            'source':         DailyBooking.BookingSource.OVERRIDE,
            'status':         DailyBooking.BookingStatus.BOOKED,
        }
    )
    return booking, None