from django.urls import path
from . import views

urlpatterns = [
    path('', views.test_list_view, name='test_list'),
    path('course/<int:course_pk>/', views.test_list_view, name='test_course_list'),
    path('create/', views.test_create_view, name='test_create_no_course'),
    path('course/<int:course_pk>/create/', views.test_create_view, name='test_create'),
    path('<int:test_id>/', views.test_detail_view, name='test_detail'),
    path('<int:test_id>/edit/', views.test_edit_view, name='test_edit'),
    path('<int:test_id>/delete/', views.test_delete_view, name='test_delete'),
    path('<int:test_id>/take/', views.test_take_view, name='test_take'),
    path('<int:test_id>/question/add/', views.question_add_view, name='question_add'),
    path('question/<int:question_id>/cases/add/', views.coding_testcase_add_view, name='coding_testcase_add'),
    path('<int:test_id>/responses/', views.test_responses_view, name='test_responses'),
    path('<int:test_id>/responses/<int:response_id>/', views.test_response_detail_view, name='test_response_detail'),
]
