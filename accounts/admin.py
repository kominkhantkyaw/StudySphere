from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {'fields': ('role', 'presence', 'status_text', 'student_id', 'bio', 'photo')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )
    list_display = ('username', 'student_id', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = BaseUserAdmin.list_filter + ('role',)
    search_fields = ('username', 'student_id', 'email', 'first_name', 'last_name')
    readonly_fields = ('student_id',)  # Auto-set for students; display only
