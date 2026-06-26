from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'account_status', 'is_staff']
    list_filter = ['role', 'account_status', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Role Info', {'fields': ('role', 'account_status', 'bio', 'profile_pic')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
