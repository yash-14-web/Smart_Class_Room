from django.contrib import admin
from .models import Assignment, Submission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display  = ['title', 'label', 'course', 'due_date', 'total_marks', 'submission_count']
    list_filter   = ['label', 'course']
    search_fields = ['title']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'submitted_at', 'grade']
    list_filter  = ['assignment__course', 'assignment__label']
