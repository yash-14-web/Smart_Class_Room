from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    path('register/',           views.register_view,        name='register'),
    path('login/',              views.login_view,           name='login'),
    path('logout/',             views.logout_view,          name='logout'),
    path('dashboard/',          views.dashboard_view,       name='dashboard'),
    path('profile/',            views.profile_view,         name='profile'),
    path('profile/update-cover/', views.update_cover_view,    name='update_cover'),
    path('change-password/',    views.change_password_view, name='change_password'),
    path('leaderboard/',        views.leaderboard_view,     name='leaderboard'),
    path('report-card/',        views.report_card_view,     name='report_card'),
    path('report-card/download/', views.download_report_pdf, name='download_report_pdf'),
    path('approval-status/',    views.approval_status_view, name='approval_status'),

    # ── Admin Panel URLs ──
    path('admin-panel/',                         admin_views.admin_dashboard,    name='admin_dashboard'),
    path('admin-panel/site-admin/',              admin_views.site_admin_view,    name='admin_site_admin'),
    path('admin-panel/site-admin/create-admin/', admin_views.admin_create,       name='admin_create'),
    # Departments
    path('admin-panel/departments/',             admin_views.department_list,    name='admin_department_list'),
    path('admin-panel/departments/create/',      admin_views.department_create,  name='admin_department_create'),
    path('admin-panel/departments/<int:pk>/edit/', admin_views.department_edit,  name='admin_department_edit'),
    # Teachers
    path('admin-panel/teachers/',                admin_views.teacher_list,       name='admin_teacher_list'),
    path('admin-panel/teachers/create/',         admin_views.teacher_create,     name='admin_teacher_create'),
    path('admin-panel/teachers/<int:pk>/approve/', admin_views.teacher_approve,  name='admin_teacher_approve'),
    path('admin-panel/teachers/<int:pk>/reject/',  admin_views.teacher_reject,   name='admin_teacher_reject'),
    path('admin-panel/teachers/<int:pk>/deactivate/', admin_views.teacher_deactivate, name='admin_teacher_deactivate'),
    # Students
    path('admin-panel/students/',                admin_views.student_list,       name='admin_student_list'),
    path('admin-panel/students/create/',         admin_views.student_create,     name='admin_student_create'),
    path('admin-panel/students/<int:pk>/approve/', admin_views.student_approve,  name='admin_student_approve'),
    path('admin-panel/students/<int:pk>/reject/',  admin_views.student_reject,   name='admin_student_reject'),
    path('admin-panel/students/<int:pk>/enroll/',  admin_views.student_enroll,   name='admin_student_enroll'),
    path('admin-panel/bulk-approve/',              admin_views.bulk_approve_users, name='bulk_approve_users'),
    # Courses
    path('admin-panel/courses/',                 admin_views.admin_course_list,   name='admin_course_list'),
    path('admin-panel/courses/create/',          admin_views.admin_course_create, name='admin_course_create'),
    path('admin-panel/courses/<int:pk>/edit/',   admin_views.admin_course_edit,   name='admin_course_edit'),
    path('admin-panel/courses/<int:pk>/approve/', admin_views.admin_course_approve, name='admin_course_approve'),
    path('admin-panel/courses/<int:pk>/reject/',  admin_views.admin_course_reject,  name='admin_course_reject'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
]
