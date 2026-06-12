from django.contrib import admin
from .models import Quiz, Question, Choice, QuizAttempt, StudentAnswer

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display  = ['title', 'course', 'total_marks', 'duration', 'is_active']
    list_filter   = ['is_active', 'course']
    inlines       = [QuestionInline]

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'quiz', 'marks', 'order']
    inlines      = [ChoiceInline]

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'score', 'is_complete', 'started_at']
    list_filter  = ['is_complete']

admin.site.register(Choice)
admin.site.register(StudentAnswer)
