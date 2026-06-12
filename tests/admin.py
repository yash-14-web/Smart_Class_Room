from django.contrib import admin
from .models import CodingTestCase, Question, StudentResponse, Test


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'total_marks', 'time_limit', 'created_at')
    search_fields = ('title', 'description', 'created_by__username')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('test', 'question_text', 'question_type', 'marks')
    search_fields = ('question_text', 'test__title')


@admin.register(CodingTestCase)
class CodingTestCaseAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_sample', 'weight')
    list_filter = ('is_sample',)


@admin.register(StudentResponse)
class StudentResponseAdmin(admin.ModelAdmin):
    list_display = ('student', 'test', 'quiz_score', 'coding_score', 'score', 'submitted_at')
    search_fields = ('student__username', 'test__title')
