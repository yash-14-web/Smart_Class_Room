from django.contrib import admin
from .models import RecordedClass


@admin.register(RecordedClass)
class RecordedClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'uploaded_by', 'uploaded_at')
    search_fields = ('title', 'subject', 'uploaded_by__username')
    list_filter = ('uploaded_at', 'subject')
