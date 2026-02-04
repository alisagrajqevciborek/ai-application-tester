from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('<int:test_run_id>/', views.report_detail, name='report-detail'),
    path('<int:test_run_id>/jira-export/', views.export_to_jira, name='export-to-jira'),
]

