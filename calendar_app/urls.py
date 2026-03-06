from django.urls import path

from . import views

app_name = 'calendar_app'

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('events/json/', views.event_list_json, name='event_list_json'),
    path('create/', views.event_create, name='event_create'),
    path('contact-support/', views.contact_support, name='contact_support'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('<int:pk>/join/', views.event_join, name='event_join'),
    path('<int:pk>/leave/', views.event_leave, name='event_leave'),
]
