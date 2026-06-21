from django.urls import path
from . import views

urlpatterns = [
    path('',          views.home_view,            name='home'),
    path('register/', views.register_view,         name='register'),
    path('login/',    views.login_view,            name='login'),
    path('login/choice/', views.login_choice_view, name='login_choice'),
    path('logout/',   views.logout_view,           name='logout'),
    path('approve/',  views.approve_students_view, name='approve_students'),
    path('students/', views.student_list_view,     name='student_list'),
    path('my-qr/',    views.my_qr_view,            name='my_qr'),
    path('staff/update-menu/', views.staff_update_menu_view, name='staff_update_menu'),
]