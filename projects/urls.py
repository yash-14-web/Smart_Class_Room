from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list_view, name='project_list'),
    path('submit/', views.project_submit_view, name='project_submit'),
    path('<int:pk>/', views.project_detail_view, name='project_detail'),
    path('<int:pk>/delete/', views.project_delete_view, name='project_delete'),
]
