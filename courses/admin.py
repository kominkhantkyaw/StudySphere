from django.contrib import admin

from .models import Certificate, Course, CourseMaterial, Enrolment, Feedback


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'created_at')
    list_filter = ('teacher',)
    search_fields = ('title', 'description')


@admin.register(Enrolment)
class EnrolmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at', 'status', 'blocked')
    list_filter = ('status', 'blocked', 'course')


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'uploaded_at')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('enrolment', 'issued_by', 'issued_at')
    list_filter = ('issued_at',)
    search_fields = ('enrolment__student__username', 'enrolment__course__title')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'rating', 'created_at')
