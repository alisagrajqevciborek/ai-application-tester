from django.urls import path
from .views import ReportDetailView

app_name = "reports"

urlpatterns = [
    path("<int:test_run_id>/", ReportDetailView.as_view(), name="detail"),
]
