from django.contrib import admin

from .models import Message, ChannelMessage, RoomPresence


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'course', 'content_preview', 'timestamp')

    @admin.display(description='Content')
    def content_preview(self, obj):
        return (obj.content or '')[:50]


@admin.register(ChannelMessage)
class ChannelMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room_name', 'content_preview', 'timestamp')
    list_filter = ('room_name',)

    @admin.display(description='Content')
    def content_preview(self, obj):
        return (obj.content or '')[:50]


@admin.register(RoomPresence)
class RoomPresenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'room_type', 'room_id', 'channel_name')
    list_filter = ('room_type',)
