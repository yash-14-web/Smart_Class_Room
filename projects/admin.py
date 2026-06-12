from django.contrib import admin
from .models import ProjectSubmission


@admin.register(ProjectSubmission)
class ProjectSubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'github_link', 'submitted_at')
    search_fields = ('title', 'student__username', 'github_link')
    list_filter = ('submitted_at',)
