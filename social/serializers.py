from rest_framework import serializers

from .models import StatusUpdate


class StatusUpdateSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.username', read_only=True,
    )

    class Meta:
        model = StatusUpdate
        fields = '__all__'
        read_only_fields = ('user', 'created_at')
