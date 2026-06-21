"""
accounts/views.py — STRICT ROLE-BASED ACCESS
Student → only student pages
Staff   → only staff pages  
Admin   → only admin pages
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
import datetime

from .models import User, StudentProfile, SystemConfig


# ── Role decorators ──────────────────────────────────────────────────────────

def student_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_choice')
        if request.user.role != 'student':
            messages.error(request, "Access denied. Students only.")
            return redirect('dashboard')
        profile = getattr(request.user, 'student_profile', None)
        if not profile or profile.registration_status != StudentProfile.RegistrationStatus.APPROVED:
            messages.error(request, "Your account is pending approval.")
            return redirect('login_choice')
        return view_func(request, *args, **kwargs)
    return _wrapped


def staff_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_choice')
        if request.user.role not in ['staff', 'admin']:
            messages.error(request, "Access denied. Staff only.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def admin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_choice')
        if request.user.role != 'admin':
            messages.error(request, "Access denied. Admins only.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


# ── Public pages ─────────────────────────────────────────────────────────────

def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


def login_choice_view(request):
    role = request.GET.get('role', '')
    return render(request, 'accounts/login_choice.html', {'role': role})


def login_view(request):
    if request.method == 'POST':
        username  = request.POST.get('username', '').strip()
        password  = request.POST.get('password', '')
        role_hint = request.POST.get('role_hint', '')  # which tab was selected

        # Check if user exists
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "❌ Username not found. Please check and try again.")
            return redirect(f'/accounts/login/choice/?role={role_hint}')

        # ── ROLE MISMATCH CHECK ──────────────────────────────────────
        if role_hint and user_obj.role != role_hint:
            role_labels = {'student': 'Student', 'staff': 'Mess Staff', 'admin': 'Admin'}
            actual  = role_labels.get(user_obj.role, user_obj.role.title())
            entered = role_labels.get(role_hint, role_hint.title())
            messages.error(request,
                f"⚠️ This account is a {actual} account, not {entered}. "
                f"Please use the {actual} login tab.")
            return redirect(f'/accounts/login/choice/?role={role_hint}')

        # Check if inactive
        if not user_obj.is_active:
            messages.error(request,
                f"⏳ Your {user_obj.role.title()} account is pending activation. "
                f"Contact admin to activate.")
            return redirect(f'/accounts/login/choice/?role={role_hint}')

        # Authenticate password
        user = authenticate(request, username=username, password=password)
        if user:
            # Students need approval
            if user.role == 'student':
                profile = getattr(user, 'student_profile', None)
                if not profile or profile.registration_status != StudentProfile.RegistrationStatus.APPROVED:
                    messages.error(request,
                        "⏳ Your student account is pending admin approval.")
                    return redirect('/accounts/login/choice/?role=student')
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}! 👋")
            return redirect('dashboard')
        else:
            messages.error(request, "❌ Wrong password. Please try again.")
            return redirect(f'/accounts/login/choice/?role={role_hint}')
    return redirect('login_choice')


def logout_view(request):
    logout(request)
    return redirect('home')


def register_view(request):
    if request.method == 'POST':
        role       = request.POST.get('role', 'student')
        username   = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        phone      = request.POST.get('phone', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')

        if not username or not password1:
            messages.error(request, "Username and password are required.")
            return render(request, 'accounts/register.html', {})
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'accounts/register.html', {})
        if len(password1) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return render(request, 'accounts/register.html', {})
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'accounts/register.html', {})

        user = User.objects.create_user(
            username=username, password=password1,
            first_name=first_name, last_name=last_name,
            email=email, phone=phone, role=role,
        )

        if role == 'student':
            roll_number = request.POST.get('roll_number', '').strip()
            department  = request.POST.get('department', '').strip()
            year        = request.POST.get('year_of_study', '')
            if not roll_number:
                user.delete()
                messages.error(request, "Roll number is required for students.")
                return render(request, 'accounts/register.html', {})
            if StudentProfile.objects.filter(roll_number=roll_number).exists():
                user.delete()
                messages.error(request, "Roll number already registered.")
                return render(request, 'accounts/register.html', {})
            StudentProfile.objects.create(
                user=user, roll_number=roll_number,
                department=department,
                year_of_study=int(year) if year.isdigit() else None,
                registration_status=StudentProfile.RegistrationStatus.PENDING,
            )
            messages.success(request, "✅ Student registration submitted! Wait for admin approval.")
        elif role == 'staff':
            # Staff starts as inactive — admin must activate
            user.is_active = False
            user.save()
            messages.success(request,
                "✅ Staff registration submitted! "
                "Admin will activate your account. "
                "Ask the admin to go to Approve Users page.")
        elif role == 'admin':
            # Admin is active immediately — set as staff for Django permissions
            user.is_active = True
            user.is_staff  = True
            user.save()
            messages.success(request,
                "✅ Admin account created successfully! You can login now.")

        return redirect('login_choice')

    return render(request, 'accounts/register.html', {})


# ── Dashboard router ──────────────────────────────────────────────────────────

@login_required(login_url='/accounts/login/choice/')
def dashboard_view(request):
    user = request.user
    if user.role == 'student':
        if not hasattr(user, 'student_profile'):
            messages.error(request, "Student profile missing. Contact admin.")
            return redirect('login_choice')
        return student_dashboard(request)
    elif user.role == 'staff':
        return staff_dashboard(request)
    elif user.role == 'admin':
        return admin_dashboard(request)
    else:
        # Fallback for superuser
        return admin_dashboard(request)


# ── Student dashboard ─────────────────────────────────────────────────────────

def student_dashboard(request):
    profile = request.user.student_profile
    today   = timezone.localdate()

    from meals.models import DailyBooking, MenuConfig, DayWiseMenu
    sessions = [
        ('breakfast', 'Breakfast', '🌅'),
        ('lunch',     'Lunch',     '☀️'),
        ('dinner',    'Dinner',    '🌙'),
    ]
    end_date    = today + datetime.timedelta(days=6)
    bookings_qs = profile.daily_bookings.filter(date__gte=today, date__lte=end_date)
    booking_map = {(b.date, b.meal_session): b for b in bookings_qs}

    week_plan    = []
    weekly_total = 0
    day_names    = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    for i in range(7):
        d     = today + datetime.timedelta(days=i)
        slots = []
        for ses, label, icon in sessions:
            b        = booking_map.get((d, ses))
            day_menu = DayWiseMenu.get_for_date(d, ses)
            if day_menu:
                has_veg      = day_menu.has_veg
                has_nonveg   = day_menu.has_nonveg
                veg_items    = day_menu.veg_items    or ''
                nonveg_items = day_menu.nonveg_items or ''
            else:
                menu         = MenuConfig.get_for_date(d, ses)
                has_veg      = menu.has_veg      if menu else False
                has_nonveg   = menu.has_nonveg   if menu else False
                veg_items    = (menu.veg_items or menu.description or '') if menu else ''
                nonveg_items = (menu.nonveg_items or '') if menu else ''

            if b:
                slots.append({
                    'session': label, 'icon': icon,
                    'meal_type': b.meal_type,
                    'price': str(b.price_snapshot) if b.price_snapshot else '0.00',
                    'status': b.status,
                    'veg_items': veg_items, 'nonveg_items': nonveg_items,
                    'has_veg': has_veg, 'has_nonveg': has_nonveg,
                })
                if b.meal_type != 'skip' and b.status != 'cancelled':
                    weekly_total += float(b.price_snapshot or 0)
            else:
                slots.append({
                    'session': label, 'icon': icon, 'meal_type': None,
                    'price': None, 'status': None,
                    'veg_items': veg_items, 'nonveg_items': nonveg_items,
                    'has_veg': has_veg, 'has_nonveg': has_nonveg,
                })

        week_plan.append({
            'date': d, 'day_name': day_names[d.weekday()],
            'date_str': d.strftime('%d %b'),
            'is_today': d == today, 'slots': slots,
        })

    upcoming = profile.daily_bookings.filter(
        date__gte=today,
        date__lte=today + datetime.timedelta(days=7),
    ).exclude(status='cancelled').exclude(meal_type='skip').order_by('date', 'meal_session')

    from billing.models import MonthlyBill
    current_month_bill = MonthlyBill.objects.filter(
        student=profile, year=today.year, month=today.month,
    ).first()

    return render(request, 'accounts/student_dashboard.html', {
        'profile': profile,
        'week_plan': week_plan,
        'weekly_total': round(weekly_total, 2),
        'upcoming': upcoming,
        'current_month_bill': current_month_bill,
        'today': today,
        'is_blocked': profile.card_status == StudentProfile.CardStatus.BLOCKED,
        'is_warning': profile.is_warning_threshold_reached(),
    })


# ── Staff dashboard ───────────────────────────────────────────────────────────

def staff_dashboard(request):
    today = timezone.localdate()
    from meals.models import DailyBooking, MenuConfig

    meal_counts = {}
    for session in ['breakfast', 'lunch', 'dinner']:
        booked   = DailyBooking.objects.filter(date=today, meal_session=session, status='booked').count()
        attended = DailyBooking.objects.filter(date=today, meal_session=session, status='attended').count()
        menu     = MenuConfig.get_for_date(today, session)
        meal_counts[session] = {'count': booked, 'attended': attended, 'menu': menu}

    all_bookings = DailyBooking.objects.filter(
        date=today
    ).exclude(meal_type='skip').select_related('student__user').order_by('meal_session', 'student__roll_number')

    return render(request, 'accounts/staff_dashboard.html', {
        'today': today,
        'meal_counts': meal_counts,
        'all_bookings': all_bookings,
    })


# ── Admin dashboard ───────────────────────────────────────────────────────────

def admin_dashboard(request):
    from accounts.models import StudentProfile
    from billing.models import MonthlyBill
    from meals.models import DailyBooking
    from django.db.models import Sum
    today = timezone.localdate()

    pending_approvals = StudentProfile.objects.filter(
        registration_status=StudentProfile.RegistrationStatus.PENDING
    ).count()
    blocked_cards = StudentProfile.objects.filter(
        card_status=StudentProfile.CardStatus.BLOCKED
    ).count()
    total_students = StudentProfile.objects.filter(
        registration_status=StudentProfile.RegistrationStatus.APPROVED
    ).count()
    month_revenue = MonthlyBill.objects.filter(
        year=today.year, month=today.month
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    total_pending = StudentProfile.objects.aggregate(
        s=Sum('pending_amount')
    )['s'] or 0
    today_meals = DailyBooking.objects.filter(
        date=today, status__in=['booked', 'attended']
    ).count()

    return render(request, 'accounts/admin_dashboard.html', {
        'pending_approvals': pending_approvals,
        'blocked_cards': blocked_cards,
        'total_students': total_students,
        'month_revenue': month_revenue,
        'total_pending': total_pending,
        'today_meals': today_meals,
        'today': today,
    })


# ── Admin views (admin_required) ──────────────────────────────────────────────

@login_required(login_url='/accounts/login/choice/')
@admin_required
def approve_students_view(request):
    pending = StudentProfile.objects.filter(
        registration_status=StudentProfile.RegistrationStatus.PENDING
    ).select_related('user')

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        action     = request.POST.get('action')
        profile    = get_object_or_404(StudentProfile, pk=student_id)
        if action == 'approve':
            profile.registration_status = StudentProfile.RegistrationStatus.APPROVED
            profile.save()
            # Also activate staff/admin users
            messages.success(request, f"{profile.user.get_full_name()} approved.")
        elif action == 'reject':
            profile.registration_status = StudentProfile.RegistrationStatus.REJECTED
            profile.save()
            messages.warning(request, f"{profile.user.get_full_name()} rejected.")
        return redirect('approve_students')

    # Handle staff/admin activation
    if request.method == 'POST':
        activate_id = request.POST.get('activate_user_id')
        action      = request.POST.get('action')
        if activate_id:
            u = get_object_or_404(User, pk=activate_id)
            if action == 'activate':
                u.is_active = True
                u.save()
                messages.success(request, f"{u.username} ({u.role}) activated.")
            elif action == 'delete_user':
                u.delete()
                messages.warning(request, "User deleted.")
            return redirect('approve_students')

    pending_users = User.objects.filter(is_active=False, role__in=['staff', 'admin'])

    return render(request, 'accounts/approve_students.html', {
        'pending': pending,
        'pending_users': pending_users,
    })


@login_required(login_url='/accounts/login/choice/')
@admin_required
def student_list_view(request):
    students = StudentProfile.objects.filter(
        registration_status=StudentProfile.RegistrationStatus.APPROVED
    ).select_related('user').order_by('roll_number')
    return render(request, 'accounts/student_list.html', {'students': students})


# ── Student views (student_required) ─────────────────────────────────────────

@login_required(login_url='/accounts/login/choice/')
@student_required
def my_qr_view(request):
    from meals.models import MealToken
    profile = request.user.student_profile
    today   = timezone.localdate()

    # Current session based on time
    current_session = MealToken.get_current_session()

    # Get/create tokens for all 3 sessions today
    sessions_info = {}
    for sess in ['breakfast', 'lunch', 'dinner']:
        token_obj = MealToken.get_or_create_token(profile, today, sess)
        sessions_info[sess] = {
            'token':   str(token_obj.token),
            'is_used': token_obj.is_used,
            'used_at': token_obj.used_at,
        }

    # Current session token for QR display
    active_token = sessions_info[current_session]['token']

    return render(request, 'accounts/my_qr.html', {
        'profile':         profile,
        'active_token':    active_token,
        'current_session': current_session,
        'sessions_info':   sessions_info,
        'today':           today,
    })


# ── Staff views ───────────────────────────────────────────────────────────────

@login_required(login_url='/accounts/login/choice/')
@staff_required
def staff_update_menu_view(request):
    if request.method == 'POST':
        from meals.models import DayWiseMenu
        session      = request.POST.get('meal_session', 'lunch')
        veg_items    = request.POST.get('veg_items', '')
        nonveg_items = request.POST.get('nonveg_items', '')
        today        = timezone.localdate()
        DayWiseMenu.objects.update_or_create(
            day_of_week=today.weekday(),
            meal_session=session,
            defaults={
                'has_veg':      bool(veg_items),
                'has_nonveg':   bool(nonveg_items),
                'veg_items':    veg_items,
                'nonveg_items': nonveg_items,
                'is_active':    True,
            }
        )
        messages.success(request, f"✅ {session.title()} menu updated!")
    return redirect('dashboard')