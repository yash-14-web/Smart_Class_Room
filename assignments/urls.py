from django.urls import path
from . import views

urlpatterns = [
    path('course/<int:course_pk>/create/',      views.assignment_create,    name='assignment_create'),
    path('<int:pk>/',                            views.assignment_detail,    name='assignment_detail'),
    path('<int:pk>/edit/',                       views.assignment_edit,      name='assignment_edit'),
    path('<int:pk>/submit/',                     views.assignment_submit,    name='assignment_submit'),
    path('submission/<int:pk>/grade/',           views.grade_submission,     name='grade_submission'),
    path('submission/<int:pk>/delete/',          views.delete_submission,    name='delete_submission'),
    path('<int:pk>/delete/',                     views.assignment_delete,    name='assignment_delete'),
    path('course/<int:course_pk>/export/csv/',   views.export_marks_csv,    name='export_marks_csv'),
    path('course/<int:course_pk>/export/excel/', views.export_marks_excel,  name='export_marks_excel'),
]
