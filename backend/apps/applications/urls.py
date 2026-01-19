from django.urls import path
from . import views

urlpatterns = [
    path('', views.application_list_create, name='application-list-create'),
    path('<int:pk>', views.application_detail, name='application-detail'),
]
