from django.urls import path
from . import views

urlpatterns = [
    path('', views.application_list_create, name='application-list-create'),
    path('<int:pk>', views.application_detail, name='application-detail'),
    path('test-runs/', views.testrun_list_create, name='testrun-list-create'),
    path('test-runs/<int:pk>', views.testrun_detail, name='testrun-detail'),
    path('test-runs/stats/', views.testrun_stats, name='testrun-stats'),
]
