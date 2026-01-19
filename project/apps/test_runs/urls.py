from django.urls import path
from .views import TestRunListCreateView, TestRunDetailView, test_run_stats

app_name = "test_runs"

urlpatterns = [
    path("", TestRunListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", TestRunDetailView.as_view(), name="detail"),
    path("stats/", test_run_stats, name="stats"),
]
