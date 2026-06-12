from django.urls import path
from . import views

urlpatterns = [
    path('register/',           views.register_view,        name='register'),
    path('login/',              views.login_view,           name='login'),
    path('logout/',             views.logout_view,          name='logout'),
    path('dashboard/',          views.dashboard_view,       name='dashboard'),
    path('profile/',            views.profile_view,         name='profile'),
    path('change-password/',    views.change_password_view, name='change_password'),
    path('leaderboard/',        views.leaderboard_view,     name='leaderboard'),
    path('report-card/',        views.report_card_view,     name='report_card'),
    path('report-card/download/', views.download_report_pdf, name='download_report_pdf'),
]
