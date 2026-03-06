from rest_framework import serializers

from .models import Course, CourseMaterial, Enrolment, Feedback


class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(
        source='teacher.get_full_name', read_only=True,
    )

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ('teacher', 'created_at', 'updated_at')


class EnrolmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrolment
        fields = '__all__'
        read_only_fields = ('student', 'enrolled_at')


class CourseMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMaterial
        fields = '__all__'


class FeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='student.username', read_only=True,
    )

    class Meta:
        model = Feedback
        fields = '__all__'
        read_only_fields = ('student', 'created_at')
