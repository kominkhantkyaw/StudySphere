from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    creator = serializers.ReadOnlyField(source='creator.username')
    course_title = serializers.ReadOnlyField(source='course.title', default=None)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'creator', 'course', 'course_title',
            'event_type', 'start', 'end', 'attendees', 'created_at',
        ]
        read_only_fields = ['creator', 'created_at']
