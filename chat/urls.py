from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_lobby, name='chat_lobby'),
    path('teachers/', views.chat_teachers_room, name='chat_teachers_room'),
    path('teachers/upload/', views.upload_teachers_attachment, name='upload_teachers_attachment'),
    path('<int:course_id>/upload/', views.upload_attachment, name='upload_attachment'),
    path('messages/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('messages/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('<int:course_id>/', views.chat_room, name='chat_room'),
]
