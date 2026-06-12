from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_card_view, name='home'),
    path('manage/', views.report_list_view, name='report_list'),
    path('<int:pk>/', views.report_detail_view, name='report_detail'),
    path('<int:pk>/edit/', views.report_edit_view, name='report_edit'),
]
