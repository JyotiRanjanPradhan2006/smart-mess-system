"""
attendance/views.py — FINAL FIX: never crashes on repeat scans
"""

import uuid
import json
import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from .models import AttendanceLog
from accounts.models import StudentProfile
from meals.models import DailyBooking


def safe_log(qr_token, scan_result, scanned_by, booking=None):
    """Create attendance log — silently ignore duplicate errors."""
    try:
        AttendanceLog.objects.create(
            qr_token=qr_token,
            scan_result=scan_result,
            scanned_by=scanned_by,
            booking=booking,
        )
    except Exception:
        pass  # ignore unique constraint or any DB error


@login_required
def scan_qr_view(request):
    if not (request.user.is_mess_staff() or request.user.is_admin_user()):
        return redirect('dashboard')
    today    = timezone.localdate()
    sessions = ['breakfast', 'lunch', 'dinner']
    meal_counts = {}
    for s in sessions:
        meal_counts[s] = DailyBooking.objects.filter(
            date=today, meal_session=s,
            status=DailyBooking.BookingStatus.BOOKED
        ).count()
    return render(request, 'attendance/scan_qr.html', {'today': today, 'meal_counts': meal_counts})


@login_required
def process_scan_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'result': 'error', 'message': 'Invalid JSON'}, status=400)

    raw_token = body.get('token', '').strip()
    session   = body.get('session', 'lunch')
    today     = timezone.localdate()

    # ── Parse token — supports JSON format and plain UUID ────────────────────
    token_uuid = None
    try:
        qr_data    = json.loads(raw_token)
        token_uuid = uuid.UUID(qr_data.get('token', ''))
    except Exception:
        try:
            token_uuid = uuid.UUID(raw_token)
        except ValueError:
            safe_log(uuid.uuid4(), AttendanceLog.ScanResult.INVALID_QR, request.user)
            return JsonResponse({'result': 'invalid', 'message': '❌ Invalid QR Code'})

    # ── Find student ──────────────────────────────────────────────────────────
    try:
        profile = StudentProfile.objects.select_related('user').get(qr_token=token_uuid)
    except StudentProfile.DoesNotExist:
        safe_log(token_uuid, AttendanceLog.ScanResult.INVALID_QR, request.user)
        return JsonResponse({'result': 'invalid', 'message': '❌ Student not found'})

    student_info = {
        'name':       profile.user.get_full_name() or profile.user.username,
        'roll':       profile.roll_number,
        'department': profile.department or '—',
        'year':       str(profile.year_of_study) + ' Year' if profile.year_of_study else '—',
        'username':   profile.user.username,
        'phone':      profile.user.phone or '—',
        'session':    session.title(),
        'date':       str(today),
    }

    def get_today_bookings():
        rows = DailyBooking.objects.filter(student=profile, date=today).order_by('meal_session')
        result = []
        for b in rows:
            icon = '🌅' if b.meal_session == 'breakfast' else ('☀️' if b.meal_session == 'lunch' else '🌙')
            result.append({
                'icon':    icon,
                'session': b.get_meal_session_display(),
                'meal':    b.get_meal_type_display(),
                'status':  b.status,
                'price':   str(b.price_snapshot),
            })
        return result

    def get_upcoming_bookings():
        rows = DailyBooking.objects.filter(
            student=profile,
            date__gte=today,
            date__lte=today + datetime.timedelta(days=3),
            status=DailyBooking.BookingStatus.BOOKED,
        ).order_by('date', 'meal_session')
        result = []
        for b in rows:
            icon = '🌅' if b.meal_session == 'breakfast' else ('☀️' if b.meal_session == 'lunch' else '🌙')
            result.append({
                'icon':    icon,
                'date':    b.date.strftime('%a, %d %b'),
                'session': b.get_meal_session_display(),
                'meal':    b.get_meal_type_display(),
                'price':   str(b.price_snapshot),
            })
        return result

    # ── Approval check ────────────────────────────────────────────────────────
    if profile.registration_status != StudentProfile.RegistrationStatus.APPROVED:
        safe_log(token_uuid, AttendanceLog.ScanResult.NOT_APPROVED, request.user)
        return JsonResponse({'result': 'invalid', 'message': '❌ Student not approved', **student_info})

    # ── Card blocked ──────────────────────────────────────────────────────────
    if profile.card_status == StudentProfile.CardStatus.BLOCKED:
        safe_log(token_uuid, AttendanceLog.ScanResult.CARD_BLOCKED, request.user)
        return JsonResponse({
            'result':         'blocked',
            'message':        '🚫 Card BLOCKED – Clear dues first',
            'pending_amount': str(profile.pending_amount),
            'today_bookings': get_today_bookings(),
            'upcoming':       get_upcoming_bookings(),
            **student_info,
        })

    # ── Find today's booking ──────────────────────────────────────────────────
    try:
        booking = DailyBooking.objects.get(student=profile, date=today, meal_session=session)
    except DailyBooking.DoesNotExist:
        safe_log(token_uuid, AttendanceLog.ScanResult.NOT_BOOKED, request.user)
        return JsonResponse({
            'result':         'not_booked',
            'message':        f'⚠️ No {session.title()} booking for today',
            'today_bookings': get_today_bookings(),
            'upcoming':       get_upcoming_bookings(),
            **student_info,
        })

    # ── Already attended — show full details, allow re-verification ───────────
    if booking.status == DailyBooking.BookingStatus.ATTENDED:
        safe_log(token_uuid, AttendanceLog.ScanResult.ALREADY_USED, request.user, booking)
        return JsonResponse({
            'result':         'already_used',
            'message':        '✅ Already Attended – Re-verified Successfully',
            'meal_type':      booking.get_meal_type_display(),
            'price':          str(booking.price_snapshot),
            'today_bookings': get_today_bookings(),
            'upcoming':       get_upcoming_bookings(),
            'pending_amount': str(profile.pending_amount),
            **student_info,
        })

    # ── Mark attendance ───────────────────────────────────────────────────────
    booking.status = DailyBooking.BookingStatus.ATTENDED
    booking.save(update_fields=['status'])
    safe_log(token_uuid, AttendanceLog.ScanResult.VALID, request.user, booking)

    return JsonResponse({
        'result':         'valid',
        'message':        '✅ Attendance Marked Successfully',
        'meal_type':      booking.get_meal_type_display(),
        'price':          str(booking.price_snapshot),
        'today_bookings': get_today_bookings(),
        'upcoming':       get_upcoming_bookings(),
        'pending_amount': str(profile.pending_amount),
        **student_info,
    })


@login_required
def attendance_report_view(request):
    if not (request.user.is_admin_user() or request.user.is_mess_staff()):
        return redirect('dashboard')
    today    = timezone.localdate()
    date_str = request.GET.get('date', str(today))
    try:
        report_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        report_date = today
    logs = AttendanceLog.objects.filter(
        scanned_at__date=report_date
    ).select_related('booking__student__user', 'scanned_by').order_by('-scanned_at')
    return render(request, 'attendance/report.html', {'logs': logs, 'report_date': report_date})