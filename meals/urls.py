"""meals/urls.py"""
from django.urls import path
from . import views

urlpatterns = [
    path('schedule/',       views.weekly_schedule_view, name='weekly_schedule'),
    path('override/',       views.daily_override_view,  name='daily_override'),
    path('history/',        views.meal_history_view,    name='meal_history'),
    path('menu/',           views.menu_management_view, name='menu_management'),
]
