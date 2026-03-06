from django.urls import path

from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('videos/', views.video_resources, name='video_resources'),
    path('create/', views.course_create, name='course_create'),
    path('my-courses/', views.my_courses, name='my_courses'),
    path('<int:pk>/', views.course_detail, name='course_detail'),
    path('<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('<int:pk>/enrol/', views.enrol, name='enrol'),
    path('<int:pk>/upload-material/', views.upload_material, name='upload_material'),
    path('<int:pk>/submit-work/', views.submit_work, name='submit_work'),
    path('<int:pk>/submissions/<int:submission_id>/edit/', views.edit_submission, name='edit_submission'),
    path('<int:pk>/submissions/<int:submission_id>/delete/', views.delete_submission, name='delete_submission'),
    path('<int:pk>/materials/<int:material_id>/edit/', views.edit_material, name='edit_material'),
    path('<int:pk>/materials/<int:material_id>/toggle-publish/', views.toggle_material_publish, name='toggle_material_publish'),
    path('<int:pk>/materials/<int:material_id>/delete/', views.delete_material, name='delete_material'),
    path('<int:pk>/feedback/', views.leave_feedback, name='leave_feedback'),
    path('<int:pk>/feedback/<int:feedback_id>/edit/', views.edit_feedback, name='edit_feedback'),
    path('<int:pk>/feedback/<int:feedback_id>/delete/', views.delete_feedback, name='delete_feedback'),
    path('<int:pk>/block/<int:student_id>/', views.block_student, name='block_student'),
    path('<int:pk>/approve/<int:student_id>/', views.approve_student, name='approve_student'),
    path('<int:pk>/reject/<int:student_id>/', views.reject_student, name='reject_student'),
    path('<int:pk>/set-enrolment-status/<int:student_id>/', views.set_enrolment_status, name='set_enrolment_status'),
    path('<int:pk>/issue-certificate/<int:student_id>/', views.issue_certificate, name='issue_certificate'),
    path('<int:pk>/revoke-certificate/<int:student_id>/', views.revoke_certificate, name='revoke_certificate'),
    path('<int:pk>/set-certificate-action/<int:student_id>/', views.set_certificate_action, name='set_certificate_action'),
    path('<int:pk>/generate-certificate/<int:student_id>/', views.generate_certificate, name='generate_certificate'),
    path('certificate/<int:enrolment_id>/download/', views.download_certificate, name='download_certificate'),
]
