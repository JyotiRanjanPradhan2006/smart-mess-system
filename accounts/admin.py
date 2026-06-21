"""accounts/admin.py"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StudentProfile, SystemConfig


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter   = ('role', 'is_active')
    fieldsets     = UserAdmin.fieldsets + (
        ('Mess System', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Mess System', {'fields': ('role', 'phone')}),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display  = ('roll_number', 'user', 'department', 'registration_status',
                     'card_status', 'pending_amount', 'paid_amount')
    list_filter   = ('registration_status', 'card_status', 'department')
    search_fields = ('roll_number', 'user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('qr_code', 'qr_token', 'pending_amount', 'paid_amount')
    actions       = ['approve_selected', 'block_cards', 'unblock_cards']

    def approve_selected(self, request, queryset):
        queryset.update(registration_status=StudentProfile.RegistrationStatus.APPROVED)
        self.message_user(request, f"{queryset.count()} students approved.")
    approve_selected.short_description = "Approve selected students"

    def block_cards(self, request, queryset):
        queryset.update(card_status=StudentProfile.CardStatus.BLOCKED)
    block_cards.short_description = "Block mess cards"

    def unblock_cards(self, request, queryset):
        queryset.update(card_status=StudentProfile.CardStatus.ACTIVE)
    unblock_cards.short_description = "Unblock mess cards"


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('pending_limit', 'warning_fraction', 'booking_deadline_hour', 'booking_deadline_minute')

    def has_add_permission(self, request):
        # Only one config row allowed
        return not SystemConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
