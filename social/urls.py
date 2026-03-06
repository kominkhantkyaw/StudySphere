from django.urls import path

from . import views

app_name = 'social'

urlpatterns = [
    path('post/', views.post_status, name='post_status'),
    path('status/<int:status_id>/delete/', views.delete_status, name='delete_status'),
    path('status/<int:status_id>/edit/', views.edit_status, name='edit_status'),
    path('status/<int:status_id>/react/', views.add_status_reaction, name='add_status_reaction'),
    path('', views.status_feed, name='status_feed'),
]
