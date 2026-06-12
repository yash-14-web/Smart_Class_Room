from django.urls import path
from . import views

urlpatterns = [
    path('', views.recorded_class_list_view, name='recorded_class_list'),
    path('upload/', views.recorded_class_upload_view, name='recorded_class_upload'),
    path('<int:pk>/edit/', views.recorded_class_edit_view, name='recorded_class_edit'),
    path('<int:pk>/delete/', views.recorded_class_delete_view, name='recorded_class_delete'),
    path('<int:pk>/', views.recorded_class_detail_view, name='recorded_class_detail'),
]
