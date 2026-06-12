from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord


class AttendanceRecordInline(admin.TabularInline):
    model  = AttendanceRecord
    extra  = 0
    fields = ['student', 'status', 'marked_by', 'marked_at']
    readonly_fields = ['marked_at']


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display  = ['course', 'date', 'topic', 'is_open',
                     'present_count', 'total_students', 'created_by']
    list_filter   = ['course', 'is_open', 'date']
    inlines       = [AttendanceRecordInline]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display  = ['student', 'session', 'status', 'marked_by', 'marked_at']
    list_filter   = ['status', 'marked_by', 'session__course']
