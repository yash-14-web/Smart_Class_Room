from django.contrib import admin
from .models import ReportCard


@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'assignment_score', 'quiz_score', 'test_score', 'overall_score', 'updated_at')
    search_fields = ('student__username',)
