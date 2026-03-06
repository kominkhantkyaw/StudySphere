from django.contrib import admin

from .models import StatusUpdate


@admin.register(StatusUpdate)
class StatusUpdateAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_preview', 'created_at')

    @admin.display(description='Content')
    def content_preview(self, obj):
        return obj.content[:50]
