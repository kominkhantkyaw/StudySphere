from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('users', views.UserViewSet)
router.register('courses', views.CourseViewSet)
router.register('feedback', views.FeedbackViewSet)
router.register('status', views.StatusUpdateViewSet)
router.register('notifications', views.NotificationViewSet, basename='notification')
router.register('materials', views.CourseMaterialViewSet)
router.register('events', views.EventViewSet, basename='event')

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='api-register'),
    path('analytics/weekly-engagement/', views.WeeklyEngagementView.as_view(), name='api-weekly-engagement'),
    path('', include(router.urls)),
]
