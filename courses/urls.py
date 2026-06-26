from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('create/', views.course_create, name='course_create'),
    path('department/<int:dept_pk>/', views.department_courses, name='department_courses'),
    path('<int:course_pk>/sessions/create/', views.create_virtual_session, name='create_virtual_session'),
    path('<int:course_pk>/ai-tutor/', views.ai_tutor_view, name='ai_tutor_view'),
    path('<int:pk>/', views.course_detail, name='course_detail'),
    path('<int:pk>/about/', views.course_about, name='course_about'),
    path('<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('<int:pk>/enroll/', views.enroll_course, name='enroll_course'),
    path('<int:pk>/unenroll/', views.unenroll_course, name='unenroll_course'),
    path('enrollment/<int:pk>/approve/', views.approve_enrollment, name='approve_enrollment'),
    path('enrollment/<int:pk>/reject/', views.reject_enrollment, name='reject_enrollment'),
    path('<int:course_id>/students/', views.get_course_students, name='get_course_students'),
]
