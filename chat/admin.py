from django.contrib import admin
from .models import Message, GroupMessage


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display  = ['sender', 'receiver', 'message', 'timestamp', 'is_read']
    list_filter   = ['is_read', 'timestamp']
    search_fields = ['sender__username', 'receiver__username', 'message']
    ordering      = ['-timestamp']


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display  = ['course', 'sender', 'message', 'timestamp']
    list_filter   = ['course']
    search_fields = ['sender__username', 'message']
    ordering      = ['-timestamp']
