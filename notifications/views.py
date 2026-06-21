"""notifications/views.py"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def notifications_view(request):
    if not request.user.is_student():
        return redirect('dashboard')

    profile = request.user.student_profile
    Notification.mark_all_read(profile)
    notifs = profile.notifications.all()[:50]
    return render(request, 'notifications/list.html', {'notifications': notifs})
