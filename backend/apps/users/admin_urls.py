from django.urls import path
from . import admin_views

urlpatterns = [
    path('users/', admin_views.admin_list_users_view, name='admin-list-users'),
    path('users/<int:user_id>/toggle-status/', admin_views.admin_toggle_user_status_view, name='admin-toggle-user-status'),
]

