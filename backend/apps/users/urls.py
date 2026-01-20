from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health_check, name='health-check'),
    path('register', views.register_view, name='register'),
    path('verify-email', views.verify_email_view, name='verify-email'),
    path('resend-code', views.resend_code_view, name='resend-code'),
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('refresh', views.refresh_token_view, name='refresh'),
    path('me', views.me_view, name='me'),
    path('change-password', views.change_password_view, name='change-password'),
]
