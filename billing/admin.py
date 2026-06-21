"""billing/admin.py"""
from django.contrib import admin
from .models import MonthlyBill, Payment


@admin.register(MonthlyBill)
class MonthlyBillAdmin(admin.ModelAdmin):
    list_display = ('student', 'year', 'month', 'total_amount', 'is_finalised')
    list_filter  = ('year', 'month', 'is_finalised')
    search_fields = ('student__roll_number',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'mode', 'reference_no', 'paid_at', 'recorded_by')
    list_filter  = ('mode',)
    date_hierarchy = 'paid_at'
    search_fields  = ('student__roll_number',)
