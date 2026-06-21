"""meals/admin.py"""
from django.contrib import admin
from .models import MenuConfig, MealPrice, WeeklySchedule, WeeklyScheduleItem, DailyBooking, DayWiseMenu


class WeeklyScheduleItemInline(admin.TabularInline):
    model = WeeklyScheduleItem
    extra = 0


@admin.register(MenuConfig)
class MenuConfigAdmin(admin.ModelAdmin):
    list_display = ('effective_date', 'meal_session', 'has_veg', 'has_nonveg', 'is_active')
    list_filter  = ('meal_session', 'has_veg', 'has_nonveg', 'is_active')
    date_hierarchy = 'effective_date'


@admin.register(MealPrice)
class MealPriceAdmin(admin.ModelAdmin):
    list_display = ('meal_type', 'meal_session', 'price', 'effective_from')
    list_filter  = ('meal_type', 'meal_session')


@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ('student', 'week_start', 'is_active', 'created_at')
    list_filter  = ('is_active',)
    inlines      = [WeeklyScheduleItemInline]


@admin.register(DailyBooking)
class DailyBookingAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'meal_session', 'meal_type', 'status', 'price_snapshot', 'source')
    list_filter  = ('status', 'meal_session', 'meal_type', 'source')
    date_hierarchy = 'date'
    search_fields  = ('student__roll_number', 'student__user__first_name')


@admin.register(DayWiseMenu)
class DayWiseMenuAdmin(admin.ModelAdmin):
    list_display  = ('get_day_of_week_display', 'get_meal_session_display',
                     'has_veg', 'has_nonveg', 'is_active')
    list_filter   = ('meal_session', 'has_veg', 'has_nonveg', 'is_active')
    ordering      = ['day_of_week', 'meal_session']