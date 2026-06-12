from django.urls import path
from . import views

urlpatterns = [
    path('course/<int:course_pk>/',          views.attendance_list,       name='attendance_list'),
    path('course/<int:course_pk>/create/',   views.create_session,        name='create_session'),
    path('session/<int:session_pk>/',        views.take_attendance,       name='take_attendance'),
    path('session/<int:session_pk>/mark/',   views.mark_self_attendance,  name='mark_self_attendance'),
    path('course/<int:course_pk>/student/',  views.student_attendance,    name='student_attendance'),
]
