from django.urls import path
from . import views

urlpatterns = [
    path('', views.application_list_create, name='application-list-create'),
    path('<int:pk>/', views.application_detail, name='application-detail'),
    path('test-runs/', views.testrun_list_create, name='testrun-list-create'),
    path('test-runs/<int:pk>/', views.testrun_detail, name='testrun-detail'),
    path('test-runs/stats/', views.testrun_stats, name='testrun-stats'),
    # Test case generator endpoints
    path('test-cases/generate/', views.generate_test_case, name='generate-test-case'),
    path('test-cases/refine/', views.refine_test_case, name='refine-test-case'),
    path('test-cases/save/', views.save_test_case, name='save-test-case'),
    path('<int:application_id>/test-cases/', views.list_test_cases, name='list-test-cases'),
    path('test-cases/<int:pk>/', views.delete_test_case, name='delete-test-case'),
    path('test-cases/<int:pk>/run/', views.run_generated_test_case, name='run-generated-test-case'),
]
