from django.contrib import admin
from .models import Course, Enrollment, Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'title', 'department', 'teacher', 'batch', 'student_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'department', 'teacher', 'batch']
    search_fields = ['course_code', 'title', 'description', 'batch']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'enrolled_at']
