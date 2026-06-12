from django.urls import path
from . import views

urlpatterns = [
    path('',                          views.inbox,               name='inbox'),
    path('<int:user_id>/',            views.chat_room,           name='chat_room'),
    path('send/<int:user_id>/',       views.send_message,        name='send_message'),
    path('fetch/<int:user_id>/',      views.fetch_messages,      name='fetch_messages'),
    path('group/<int:course_id>/',    views.group_chat,          name='group_chat'),
    path('group/fetch/<int:course_id>/', views.fetch_group_messages, name='fetch_group_messages'),
]
