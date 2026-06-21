"""notifications/context_processors.py"""


def unread_notifications(request):
    count = 0
    if request.user.is_authenticated and request.user.is_student():
        try:
            profile = request.user.student_profile
            count = profile.notifications.filter(is_read=False).count()
        except Exception:
            pass
    return {'unread_notification_count': count}
