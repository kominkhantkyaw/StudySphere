from django.contrib import admin
from .models import Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'action_type', 'timestamp')
    list_filter = ('action_type', 'timestamp')
    search_fields = ('user__username', 'course__title')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
