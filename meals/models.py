"""
meals/models.py
Covers: Menu configuration, Meal pricing, Weekly schedule, Daily bookings
"""

from django.db import models
from django.utils import timezone
from django.conf import settings
import datetime


class MealType(models.TextChoices):
    VEG    = 'veg',    'Vegetarian'
    NONVEG = 'nonveg', 'Non-Vegetarian'
    SKIP   = 'skip',   'Skip (Not Eating)'


class DayOfWeek(models.IntegerChoices):
    MONDAY    = 0, 'Monday'
    TUESDAY   = 1, 'Tuesday'
    WEDNESDAY = 2, 'Wednesday'
    THURSDAY  = 3, 'Thursday'
    FRIDAY    = 4, 'Friday'
    SATURDAY  = 5, 'Saturday'
    SUNDAY    = 6, 'Sunday'


class MenuConfig(models.Model):
    """
    Admin sets daily menu – controls which meal types are available.
    Multiple configs can exist; the active one per date is used.
    """

    class MealSession(models.TextChoices):
        BREAKFAST = 'breakfast', 'Breakfast'
        LUNCH     = 'lunch',     'Lunch'
        DINNER    = 'dinner',    'Dinner'

    class DayOfWeek(models.IntegerChoices):
        MONDAY    = 0, 'Monday'
        TUESDAY   = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY  = 3, 'Thursday'
        FRIDAY    = 4, 'Friday'
        SATURDAY  = 5, 'Saturday'
        SUNDAY    = 6, 'Sunday'
        ALL_DAYS  = 7, 'All Days (Default)'

    effective_date = models.DateField(help_text="Date from which this menu applies")
    day_of_week    = models.IntegerField(
        choices=DayOfWeek.choices,
        default=7,
        help_text="Set a specific day or 'All Days' as default"
    )
    meal_session   = models.CharField(max_length=10, choices=MealSession.choices, default=MealSession.LUNCH)
    has_veg        = models.BooleanField(default=True)
    has_nonveg     = models.BooleanField(default=False)
    description        = models.TextField(blank=True, help_text="General description (optional)")
    veg_items          = models.TextField(blank=True, help_text="Veg food items e.g: Dal, Rice, Roti, Sabzi")
    nonveg_items       = models.TextField(blank=True, help_text="Non-Veg food items e.g: Chicken Curry, Rice, Roti")
    is_active      = models.BooleanField(default=True)
    created_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='menu_configs'
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Menu Configuration'
        unique_together = ('effective_date', 'meal_session', 'day_of_week')
        ordering = ['-effective_date', 'meal_session']

    def __str__(self):
        options = []
        if self.has_veg:    options.append('Veg')
        if self.has_nonveg: options.append('NonVeg')
        return f"{self.effective_date} | {self.get_meal_session_display()} | {' & '.join(options)}"

    @classmethod
    def get_for_date(cls, date, session=None):
        """
        Return menu for this specific date+day_of_week.
        Priority: exact day_of_week match > ALL_DAYS fallback
        """
        qs = cls.objects.filter(effective_date__lte=date, is_active=True)
        if session:
            qs = qs.filter(meal_session=session)

        # First try exact day of week match
        day_num = date.weekday()  # 0=Mon ... 6=Sun
        exact = qs.filter(day_of_week=day_num).order_by('-effective_date').first()
        if exact:
            return exact

        # Fallback to ALL_DAYS (7)
        return qs.filter(day_of_week=7).order_by('-effective_date').first()

    def allowed_choices(self):
        choices = [MealType.SKIP]
        if self.has_veg:    choices.append(MealType.VEG)
        if self.has_nonveg: choices.append(MealType.NONVEG)
        return choices


class MealPrice(models.Model):
    """
    Price per meal type.  A snapshot is stored on each booking so
    historical billing is correct after price changes.
    """
    meal_type      = models.CharField(max_length=10, choices=MealType.choices)
    meal_session   = models.CharField(
        max_length=10,
        choices=MenuConfig.MealSession.choices,
        default=MenuConfig.MealSession.LUNCH,
    )
    price          = models.DecimalField(max_digits=8, decimal_places=2)
    effective_from = models.DateField(default=timezone.localdate)
    created_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='price_changes'
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_from']
        verbose_name = 'Meal Price'

    def __str__(self):
        return f"{self.get_meal_type_display()} / {self.get_meal_session_display()} – ₹{self.price} (from {self.effective_from})"

    @classmethod
    def get_price_for(cls, meal_type, session, date):
        """Fetch the active price on `date` for the given type+session."""
        obj = cls.objects.filter(
            meal_type=meal_type,
            meal_session=session,
            effective_from__lte=date,
        ).order_by('-effective_from').first()
        return obj.price if obj else 0


class WeeklySchedule(models.Model):
    """
    Student's recurring weekly meal plan.
    One active schedule per student at a time.
    """
    student    = models.ForeignKey(
        'accounts.StudentProfile', on_delete=models.CASCADE, related_name='weekly_schedules'
    )
    week_start = models.DateField(help_text="Monday of the week this schedule applies from")
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-week_start']
        verbose_name = 'Weekly Schedule'

    def __str__(self):
        return f"{self.student} – week of {self.week_start}"

    def estimated_weekly_cost(self):
        """Sum of price snapshots for non-skip items in this schedule."""
        total = 0
        for item in self.items.exclude(meal_preference=MealType.SKIP):
            date = self.week_start + datetime.timedelta(days=item.day_of_week)
            price = MealPrice.get_price_for(item.meal_preference, item.meal_session, date)
            total += price
        return total

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=['is_active'])


class WeeklyScheduleItem(models.Model):
    """A single day+session slot within a WeeklySchedule."""

    schedule        = models.ForeignKey(WeeklySchedule, on_delete=models.CASCADE, related_name='items')
    day_of_week     = models.IntegerField(choices=DayOfWeek.choices)
    meal_session    = models.CharField(
        max_length=10,
        choices=MenuConfig.MealSession.choices,
        default=MenuConfig.MealSession.LUNCH,
    )
    meal_preference = models.CharField(
        max_length=10,
        choices=MealType.choices,
        default=MealType.VEG,
    )

    class Meta:
        unique_together = ('schedule', 'day_of_week', 'meal_session')
        ordering = ['day_of_week', 'meal_session']

    def __str__(self):
        return (
            f"{self.get_day_of_week_display()} | {self.get_meal_session_display()} "
            f"→ {self.get_meal_preference_display()}"
        )


class DailyBooking(models.Model):
    """
    A concrete meal booking for one student on one date+session.
    Created automatically from WeeklySchedule; can be overridden.
    """

    class BookingStatus(models.TextChoices):
        BOOKED    = 'booked',    'Booked'
        ATTENDED  = 'attended',  'Attended'
        MISSED    = 'missed',    'Missed (Still Billed)'
        CANCELLED = 'cancelled', 'Cancelled'

    class BookingSource(models.TextChoices):
        AUTO     = 'auto',     'Auto (Weekly Schedule)'
        OVERRIDE = 'override', 'Manual Override'

    student         = models.ForeignKey(
        'accounts.StudentProfile', on_delete=models.CASCADE, related_name='daily_bookings'
    )
    date            = models.DateField()
    meal_session    = models.CharField(max_length=10, choices=MenuConfig.MealSession.choices)
    meal_type       = models.CharField(max_length=10, choices=MealType.choices)
    status          = models.CharField(
        max_length=10, choices=BookingStatus.choices, default=BookingStatus.BOOKED
    )
    source          = models.CharField(
        max_length=10, choices=BookingSource.choices, default=BookingSource.AUTO
    )
    price_snapshot  = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Price at time of booking (immutable for billing)"
    )
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'date', 'meal_session')
        ordering = ['-date', 'meal_session']
        verbose_name = 'Daily Booking'

    def __str__(self):
        return (
            f"{self.student.roll_number} | {self.date} | "
            f"{self.get_meal_session_display()} | {self.get_meal_type_display()} | {self.status}"
        )

    def is_billable(self):
        """Skip and Cancelled are not billed; everything else is."""
        return self.meal_type != MealType.SKIP and self.status != self.BookingStatus.CANCELLED

    def can_be_modified(self):
        """Student can change before deadline and only if date is today or future."""
        from accounts.models import SystemConfig
        cfg = SystemConfig.get_solo()
        today = timezone.localdate()
        if self.date < today:
            return False
        if self.date == today and cfg.booking_deadline_passed():
            return False
        return True


class DayWiseMenu(models.Model):
    """
    Admin sets different food items for each day of week per session.
    This repeats every week — Mon Breakfast always shows its own menu.
    """
    day_of_week  = models.IntegerField(choices=DayOfWeek.choices)
    meal_session = models.CharField(max_length=10, choices=MenuConfig.MealSession.choices)
    has_veg      = models.BooleanField(default=True)
    has_nonveg   = models.BooleanField(default=False)
    veg_items    = models.TextField(blank=True, help_text="Veg food items for this day")
    nonveg_items = models.TextField(blank=True, help_text="Non-Veg food items for this day")
    is_active    = models.BooleanField(default=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('day_of_week', 'meal_session')
        ordering = ['day_of_week', 'meal_session']
        verbose_name = 'Day-Wise Menu'
        verbose_name_plural = 'Day-Wise Menus'

    def __str__(self):
        return f"{self.get_day_of_week_display()} | {self.get_meal_session_display()}"

    @classmethod
    def get_for_date(cls, date, session):
        """Return the menu for a specific date's weekday."""
        try:
            return cls.objects.get(
                day_of_week=date.weekday(),
                meal_session=session,
                is_active=True
            )
        except cls.DoesNotExist:
            return None


import uuid as _uuid

class MealToken(models.Model):
    """One-time QR token per student per session per day."""
    student    = models.ForeignKey(
        'accounts.StudentProfile', on_delete=models.CASCADE,
        related_name='meal_tokens'
    )
    token      = models.UUIDField(default=_uuid.uuid4, unique=True)
    date       = models.DateField()
    session    = models.CharField(max_length=15, choices=[
        ('breakfast','Breakfast'), ('lunch','Lunch'), ('dinner','Dinner')
    ])
    is_used    = models.BooleanField(default=False)
    used_at    = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date', 'session')
        ordering = ['-created_at']
        verbose_name = 'Meal Token'

    def __str__(self):
        return f"{self.student.roll_number} | {self.date} | {self.session}"

    @classmethod
    def get_or_create_token(cls, student, date, session):
        obj, _ = cls.objects.get_or_create(
            student=student, date=date, session=session,
            defaults={'token': _uuid.uuid4(), 'is_used': False}
        )
        return obj

    @classmethod
    def get_current_session(cls):
        from django.utils import timezone
        hour = timezone.localtime(timezone.now()).hour
        if 6 <= hour < 11:   return 'breakfast'
        elif 11 <= hour < 16: return 'lunch'
        else:                  return 'dinner'