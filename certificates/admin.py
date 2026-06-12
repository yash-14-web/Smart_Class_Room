from django.contrib import admin
from .models import Certificate

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'badge_type', 'issued_by', 'issued_at']
    list_filter  = ['badge_type', 'course']
    search_fields= ['student__username', 'course__title']
