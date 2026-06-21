"""
meals/views.py  — FIXED
Weekly schedule management, daily override, meal history.
"""

import datetime
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import WeeklySchedule, WeeklyScheduleItem, DailyBooking, MenuConfig, MealType, DayOfWeek
from .services import generate_bookings_from_schedule, override_daily_booking
from accounts.models import StudentProfile


def require_approved_student(view_func):
    from functools import wraps
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_student():
            return redirect('login')
        profile = request.user.student_profile
        if profile.registration_status != StudentProfile.RegistrationStatus.APPROVED:
            messages.error(request, "Your account is pending approval.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped


@login_required
@require_approved_student
def weekly_schedule_view(request):
    profile    = request.user.student_profile
    today      = timezone.localdate()
    week_start = today - datetime.timedelta(days=today.weekday())

    active_schedule = profile.weekly_schedules.filter(is_active=True).first()

    sessions = ['breakfast', 'lunch', 'dinner']
    days     = list(DayOfWeek.choices)

    # Existing preferences {(day_val, session): preference}
    pref_map = {}
    if active_schedule:
        for item in active_schedule.items.all():
            pref_map[(item.day_of_week, item.meal_session)] = item.meal_preference

    # Allowed choices per session
    menu_choices = {}
    for s in sessions:
        menu = MenuConfig.get_for_date(week_start, s)
        menu_choices[s] = menu.allowed_choices() if menu else [MealType.SKIP]

    # Pre-build grid so template needs zero dict-lookup logic
    grid = []
    for day_val, day_name in days:
        row = {'day_val': day_val, 'day_name': day_name, 'sessions': []}
        for s in sessions:
            allowed  = menu_choices.get(s, [MealType.SKIP])
            current  = pref_map.get((day_val, s), MealType.SKIP)
            row['sessions'].append({
                'session':       s,
                'session_label': s.title(),
                'choices':       allowed,
                'current_pref':  current,
            })
        grid.append(row)

    if request.method == 'POST':
        if profile.card_status == StudentProfile.CardStatus.BLOCKED:
            messages.error(request, "Your card is blocked. Clear pending dues to reschedule.")
            return redirect('weekly_schedule')

        profile.weekly_schedules.filter(is_active=True).update(is_active=False)
        schedule = WeeklySchedule.objects.create(
            student=profile, week_start=week_start, is_active=True
        )
        for day_val, _ in days:
            for s in sessions:
                pref    = request.POST.get(f"meal_{day_val}_{s}", MealType.SKIP)
                allowed = menu_choices.get(s, [MealType.SKIP])
                if pref not in allowed:
                    pref = MealType.SKIP
                WeeklyScheduleItem.objects.create(
                    schedule=schedule,
                    day_of_week=day_val,
                    meal_session=s,
                    meal_preference=pref,
                )

        bookings_created = generate_bookings_from_schedule(schedule, weeks_ahead=4)
        messages.success(
            request,
            f"Weekly schedule saved! {len(bookings_created)} bookings created. "
            f"Estimated weekly cost: Rs.{schedule.estimated_weekly_cost()}"
        )
        return redirect('weekly_schedule')

    ctx = {
        'active_schedule': active_schedule,
        'grid':            grid,
        'sessions':        sessions,
        'estimated_cost':  active_schedule.estimated_weekly_cost() if active_schedule else 0,
    }
    return render(request, 'meals/weekly_schedule.html', ctx)


@login_required
@require_approved_student
def daily_override_view(request):
    profile = request.user.student_profile
    today   = timezone.localdate()
    sessions = ['breakfast', 'lunch', 'dinner']
    upcoming_dates = [today + datetime.timedelta(days=i) for i in range(7)]

    booking_map = {}
    for b in profile.daily_bookings.filter(
        date__gte=today, date__lt=today + datetime.timedelta(days=7)
    ):
        booking_map[(str(b.date), b.meal_session)] = b

    override_grid = []
    for d in upcoming_dates:
        row = {'date': d, 'is_today': d == today, 'sessions': []}
        for s in sessions:
            menu    = MenuConfig.get_for_date(d, s)
            allowed = menu.allowed_choices() if menu else [MealType.SKIP]
            booking = booking_map.get((str(d), s))
            row['sessions'].append({
                'session':       s,
                'session_label': s.title(),
                'allowed':       allowed,
                'booking':       booking,
                'current_type':  booking.meal_type if booking else MealType.SKIP,
            })
        override_grid.append(row)

    if request.method == 'POST':
        date_str = request.POST.get('date')
        session  = request.POST.get('session')
        meal     = request.POST.get('meal_type')
        try:
            date = datetime.date.fromisoformat(date_str)
        except (ValueError, TypeError):
            messages.error(request, "Invalid date.")
            return redirect('daily_override')
        booking, error = override_daily_booking(profile, date, session, meal)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, f"Booking updated: {date} {session} -> {meal}")
        return redirect('daily_override')

    ctx = {
        'override_grid': override_grid,
        'meal_types':    MealType.choices,
        'today':         today,
    }
    return render(request, 'meals/daily_override.html', ctx)


@login_required
@require_approved_student
def meal_history_view(request):
    profile = request.user.student_profile
    today   = timezone.localdate()

    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))

    from django.db.models import Case, When, IntegerField
    session_order = Case(
        When(meal_session='breakfast', then=0),
        When(meal_session='lunch',     then=1),
        When(meal_session='dinner',    then=2),
        output_field=IntegerField(),
    )

    bookings = list(profile.daily_bookings.filter(
        date__year=year, date__month=month
    ).annotate(session_order=session_order).order_by('date', 'session_order'))

    total_billed = sum(
        b.price_snapshot for b in bookings
        if b.is_billable()
    )

    months = [(m, datetime.date(today.year, m, 1).strftime('%B')) for m in range(1, 13)]

    ctx = {
        'bookings':       bookings,
        'total_billed':   total_billed,
        'selected_year':  year,
        'selected_month': month,
        'months':         months,
        'year_range':     range(today.year - 1, today.year + 1),
    }
    return render(request, 'meals/meal_history.html', ctx)

@login_required
def menu_management_view(request):
    if not request.user.is_admin_user():
        return redirect('dashboard')
    from .models import MenuConfig, MealPrice
    menus  = MenuConfig.objects.all()[:30]
    prices = MealPrice.objects.all()[:20]
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_menu':
            from .forms import MenuConfigForm
            form = MenuConfigForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.created_by = request.user
                obj.save()
                messages.success(request, "Menu updated. Students notified.")
            else:
                messages.error(request, f"Errors: {form.errors}")
        elif action == 'update_price':
            from .forms import MealPriceForm
            form = MealPriceForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.created_by = request.user
                obj.save()
                messages.success(request, "Price updated. Students notified.")
            else:
                messages.error(request, f"Errors: {form.errors}")
        return redirect('menu_management')
    from .forms import MenuConfigForm, MealPriceForm
    ctx = {
        'menus':      menus,
        'prices':     prices,
        'menu_form':  MenuConfigForm(),
        'price_form': MealPriceForm(),
    }
    return render(request, 'meals/menu_management.html', ctx)