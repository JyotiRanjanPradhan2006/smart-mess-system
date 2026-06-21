from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/accounts/', permanent=False)),
    path('accounts/', include('accounts.urls')),
    path('meals/', include('meals.urls')),
    path('billing/', include('billing.urls')),
    path('notifications/', include('notifications.urls')),
    path('attendance/', include('attendance.urls')),
    path('dashboard/', include('accounts.dashboard_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom admin site branding
admin.site.site_header = "🍽️ Mess Management Admin"
admin.site.site_title = "Mess Admin"
admin.site.index_title = "Smart Mess Scheduling & Billing"