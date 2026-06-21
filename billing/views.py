"""
billing/views.py
Monthly bill view, payment recording, revenue dashboard.
"""

import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from .models import MonthlyBill, Payment
from .services import recalculate_student_bill
from accounts.models import StudentProfile


@login_required
def billing_summary_view(request):
    """Student: view their own billing history."""
    if not request.user.is_student():
        return redirect('dashboard')

    profile = request.user.student_profile
    today   = timezone.localdate()

    year  = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # Recalculate and fetch
    bill = recalculate_student_bill(profile, year, month)

    all_bills = profile.monthly_bills.order_by('-year', '-month')
    payments  = profile.payments.order_by('-paid_at')[:10]

    months = [(m, datetime.date(today.year, m, 1).strftime('%B')) for m in range(1, 13)]

    ctx = {
        'profile': profile,
        'bill': bill,
        'all_bills': all_bills,
        'payments': payments,
        'selected_year': year,
        'selected_month': month,
        'months': months,
        'year_range': range(today.year - 1, today.year + 1),
    }
    return render(request, 'billing/summary.html', ctx)


@login_required
def admin_billing_view(request):
    """Admin: see all students' billing, record payments."""
    if not request.user.is_admin_user():
        return redirect('dashboard')

    today = timezone.localdate()

    # Recalculate all students this month
    if request.method == 'POST' and request.POST.get('action') == 'recalculate_all':
        for p in StudentProfile.objects.filter(
            registration_status=StudentProfile.RegistrationStatus.APPROVED
        ):
            recalculate_student_bill(p, today.year, today.month)
        messages.success(request, "All bills recalculated.")
        return redirect('admin_billing')

    if request.method == 'POST' and request.POST.get('action') == 'record_payment':
        student_id = request.POST.get('student_id')
        amount     = request.POST.get('amount')
        mode       = request.POST.get('mode', 'cash')
        ref        = request.POST.get('reference_no', '')
        profile    = get_object_or_404(StudentProfile, pk=student_id)
        try:
            amt = float(amount)
            if amt <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount.")
            return redirect('admin_billing')

        Payment.objects.create(
            student=profile,
            amount=amt,
            mode=mode,
            reference_no=ref,
            recorded_by=request.user,
        )
        recalculate_student_bill(profile, today.year, today.month)
        messages.success(request, f"Payment ₹{amt} recorded for {profile.user.get_full_name()}.")
        return redirect('admin_billing')

    students = StudentProfile.objects.filter(
        registration_status=StudentProfile.RegistrationStatus.APPROVED
    ).select_related('user').order_by('-pending_amount')

    total_revenue = MonthlyBill.objects.filter(
        year=today.year, month=today.month
    ).aggregate(t=Sum('total_amount'))['t'] or 0

    total_pending = StudentProfile.objects.aggregate(
        t=Sum('pending_amount')
    )['t'] or 0

    payment_modes = Payment.PaymentMode.choices

    ctx = {
        'students': students,
        'today': today,
        'total_revenue': total_revenue,
        'total_pending': total_pending,
        'payment_modes': payment_modes,
    }
    return render(request, 'billing/admin_billing.html', ctx)


@login_required
def revenue_dashboard_view(request):
    """Admin: analytics / revenue overview."""
    if not request.user.is_admin_user():
        return redirect('dashboard')

    today = timezone.localdate()

    # Monthly revenue last 6 months
    months_data = []
    for i in range(5, -1, -1):
        d = today.replace(day=1) - datetime.timedelta(days=1) * (i * 28)
        total = MonthlyBill.objects.filter(year=d.year, month=d.month).aggregate(
            t=Sum('total_amount')
        )['t'] or 0
        months_data.append({
            'label': d.strftime('%b %Y'),
            'total': float(total),
        })

    # Blocked cards
    blocked = StudentProfile.objects.filter(
        card_status=StudentProfile.CardStatus.BLOCKED
    ).select_related('user')

    ctx = {
        'months_data': months_data,
        'blocked_students': blocked,
        'today': today,
    }
    return render(request, 'billing/revenue_dashboard.html', ctx)
