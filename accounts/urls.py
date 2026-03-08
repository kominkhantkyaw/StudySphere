from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('contact/', views.contact_view, name='contact'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('search/', views.search_users, name='search_users'),
    path('my-students/', views.my_students, name='my_students'),
    path('set-presence/', views.set_presence, name='set_presence'),
    path('set-theme/', views.set_theme, name='set_theme'),
    path('set-language/', views.set_language, name='set_language'),
    path('settings/security/2fa/setup/', views.two_factor_setup, name='two_factor_setup'),
    path('settings/security/2fa/verify-setup/', views.two_factor_verify_setup, name='two_factor_verify_setup'),
    path('settings/security/2fa/disable/', views.two_factor_disable, name='two_factor_disable'),
    path('login/2fa/', views.two_factor_verify, name='two_factor_verify'),

    # Password reset (via email link)
    path(
        'password-reset/',
        views.PasswordResetView.as_view(),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/accounts/reset/done/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
    path(
        'password-change/',
        auth_views.PasswordChangeView.as_view(
            template_name='accounts/password_change.html',
            success_url='/accounts/password-change/done/',
        ),
        name='password_change',
    ),
    path(
        'password-change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='accounts/password_change_done.html',
        ),
        name='password_change_done',
    ),
]
