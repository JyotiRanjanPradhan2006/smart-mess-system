"""billing/urls.py"""
from django.urls import path
from . import views

urlpatterns = [
    path('summary/',   views.billing_summary_view,  name='billing_summary'),
    path('admin/',     views.admin_billing_view,     name='admin_billing'),
    path('revenue/',   views.revenue_dashboard_view, name='revenue_dashboard'),
]
