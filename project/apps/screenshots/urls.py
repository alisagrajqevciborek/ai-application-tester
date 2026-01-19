from django.urls import path
from .views import ScreenshotListView

app_name = "screenshots"

urlpatterns = [
    path("<int:test_run_id>/", ScreenshotListView.as_view(), name="list"),
]
