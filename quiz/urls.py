from django.urls import path
from . import views

urlpatterns = [
    path('course/<int:course_pk>/',                views.quiz_list,               name='quiz_list'),
    path('course/<int:course_pk>/create/',         views.quiz_create,             name='quiz_create'),
    path('<int:quiz_pk>/edit/',                    views.quiz_edit,               name='quiz_edit'),
    path('<int:quiz_pk>/questions/',               views.quiz_add_questions,      name='quiz_add_questions'),
    path('<int:quiz_pk>/attempt/',                 views.quiz_attempt,            name='quiz_attempt'),
    path('result/<int:attempt_pk>/',               views.quiz_result,             name='quiz_result'),
    path('<int:quiz_pk>/submissions/',             views.quiz_submissions,        name='quiz_submissions'),
    path('<int:quiz_pk>/students/',                views.quiz_attempted_students, name='quiz_attempted_students'),
    path('<int:quiz_pk>/delete/',                  views.quiz_delete,             name='quiz_delete'),
    path('question/<int:question_pk>/delete/',     views.delete_question,         name='delete_question'),
]
