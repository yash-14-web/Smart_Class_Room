"""
Admin Panel Views for Smart Classroom
Handles: Dashboard, Departments, Teachers, Students, Courses management
Only accessible by superusers (Admin role)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from users.models import CustomUser
from courses.models import Course, Department, Enrollment


def is_admin(user):
    """Check if user is a superuser (Admin)."""
    return user.is_superuser


# ──────────────────────────────────────────────────────────
# ADMIN DASHBOARD
# ──────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_departments = Department.objects.filter(is_active=True).count()
    total_courses = Course.objects.count()
    total_teachers = CustomUser.objects.filter(role='teacher').count()
    total_students = CustomUser.objects.filter(role='student').count()
    pending_teachers = CustomUser.objects.filter(role='teacher', account_status='pending').count()
    pending_students = CustomUser.objects.filter(role='student', account_status='pending').count()
    active_courses = Course.objects.filter(is_active=True).count()

    recent_teachers = CustomUser.objects.filter(role='teacher').order_by('-date_joined')[:5]
    recent_students = CustomUser.objects.filter(role='student').order_by('-date_joined')[:5]

    context = {
        'total_departments': total_departments,
        'total_courses': total_courses,
        'total_teachers': total_teachers,
        'total_students': total_students,
        'pending_teachers': pending_teachers,
        'pending_students': pending_students,
        'active_courses': active_courses,
        'recent_teachers': recent_teachers,
        'recent_students': recent_students,
        'total_pending': pending_teachers + pending_students,
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ──────────────────────────────────────────────────────────
# DEPARTMENT MANAGEMENT
# ──────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def department_list(request):
    departments = Department.objects.annotate(
        course_count=Count('courses')
    ).order_by('-created_at')
    return render(request, 'admin_panel/department_list.html', {'departments': departments})


@login_required
@user_passes_test(is_admin)
def department_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '').strip()

        if not name or not code:
            messages.error(request, 'Department name and code are required.')
            return render(request, 'admin_panel/department_form.html', {
                'form_data': request.POST, 'is_edit': False
            })

        if Department.objects.filter(code=code).exists():
            messages.error(request, f'Department code "{code}" already exists.')
            return render(request, 'admin_panel/department_form.html', {
                'form_data': request.POST, 'is_edit': False
            })

        cover_image = request.FILES.get('cover_image')
        Department.objects.create(name=name, code=code, description=description, cover_image=cover_image)
        messages.success(request, f'Department "{name}" created successfully!')
        return redirect('admin_department_list')

    return render(request, 'admin_panel/department_form.html', {'is_edit': False})


@login_required
@user_passes_test(is_admin)
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        dept.name = request.POST.get('name', '').strip()
        dept.code = request.POST.get('code', '').strip().upper()
        dept.description = request.POST.get('description', '').strip()
        dept.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('cover_image'):
            dept.cover_image = request.FILES.get('cover_image')

        if Department.objects.filter(code=dept.code).exclude(pk=pk).exists():
            messages.error(request, f'Department code "{dept.code}" already exists.')
            return render(request, 'admin_panel/department_form.html', {
                'dept': dept, 'is_edit': True
            })

        dept.save()
        messages.success(request, f'Department "{dept.name}" updated.')
        return redirect('admin_department_list')

    return render(request, 'admin_panel/department_form.html', {'dept': dept, 'is_edit': True})


# ──────────────────────────────────────────────────────────
# TEACHER MANAGEMENT
# ──────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def teacher_list(request):
    status_filter = request.GET.get('status', 'all')
    teachers = CustomUser.objects.filter(role='teacher').order_by('-date_joined')
    if status_filter != 'all':
        teachers = teachers.filter(account_status=status_filter)

    pending_count = CustomUser.objects.filter(role='teacher', account_status='pending').count()
    return render(request, 'admin_panel/teacher_list.html', {
        'teachers': teachers,
        'status_filter': status_filter,
        'pending_count': pending_count,
    })


@login_required
@user_passes_test(is_admin)
def teacher_create(request):
    departments = Department.objects.filter(is_active=True)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return render(request, 'admin_panel/teacher_form.html', {
                'form_data': request.POST, 'departments': departments, 'is_edit': False
            })

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return render(request, 'admin_panel/teacher_form.html', {
                'form_data': request.POST, 'departments': departments, 'is_edit': False
            })

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role='teacher',
            account_status='active',
        )
        messages.success(request, f'Teacher "{username}" created and activated!')
        return redirect('admin_teacher_list')

    return render(request, 'admin_panel/teacher_form.html', {
        'departments': departments, 'is_edit': False
    })


@login_required
@user_passes_test(is_admin)
def teacher_approve(request, pk):
    teacher = get_object_or_404(CustomUser, pk=pk, role='teacher')
    teacher.account_status = 'active'
    teacher.save()
    messages.success(request, f'Teacher "{teacher.username}" approved!')
    return redirect('admin_teacher_list')


@login_required
@user_passes_test(is_admin)
def teacher_reject(request, pk):
    teacher = get_object_or_404(CustomUser, pk=pk, role='teacher')
    teacher.account_status = 'rejected'
    teacher.save()
    messages.warning(request, f'Teacher "{teacher.username}" rejected.')
    return redirect('admin_teacher_list')


@login_required
@user_passes_test(is_admin)
def teacher_deactivate(request, pk):
    teacher = get_object_or_404(CustomUser, pk=pk, role='teacher')
    teacher.account_status = 'rejected'
    teacher.is_active = False
    teacher.save()
    messages.warning(request, f'Teacher "{teacher.username}" deactivated.')
    return redirect('admin_teacher_list')


# ──────────────────────────────────────────────────────────
# STUDENT MANAGEMENT
# ──────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def student_list(request):
    status_filter = request.GET.get('status', 'all')
    students = CustomUser.objects.filter(role='student').order_by('-date_joined')
    if status_filter != 'all':
        students = students.filter(account_status=status_filter)

    pending_count = CustomUser.objects.filter(role='student', account_status='pending').count()
    return render(request, 'admin_panel/student_list.html', {
        'students': students,
        'status_filter': status_filter,
        'pending_count': pending_count,
    })


@login_required
@user_passes_test(is_admin)
def student_create(request):
    courses = Course.objects.filter(is_active=True)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '').strip()
        selected_courses = request.POST.getlist('courses')

        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return render(request, 'admin_panel/student_form.html', {
                'form_data': request.POST, 'courses': courses, 'is_edit': False
            })

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return render(request, 'admin_panel/student_form.html', {
                'form_data': request.POST, 'courses': courses, 'is_edit': False
            })

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role='student',
            account_status='active',
        )

        # Enroll in selected courses
        for course_id in selected_courses:
            try:
                course = Course.objects.get(pk=course_id)
                Enrollment.objects.get_or_create(student=user, course=course)
            except Course.DoesNotExist:
                pass

        messages.success(request, f'Student "{username}" created and enrolled in {len(selected_courses)} course(s)!')
        return redirect('admin_student_list')

    return render(request, 'admin_panel/student_form.html', {
        'courses': courses, 'is_edit': False
    })


@login_required
@user_passes_test(is_admin)
def student_approve(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, role='student')
    student.account_status = 'active'
    student.save()
    messages.success(request, f'Student "{student.username}" approved!')
    return redirect('admin_student_list')


@login_required
@user_passes_test(is_admin)
def student_reject(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, role='student')
    student.account_status = 'rejected'
    student.save()
    messages.warning(request, f'Student "{student.username}" rejected.')
    return redirect('admin_student_list')


@login_required
@user_passes_test(is_admin)
def student_enroll(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, role='student')
    courses = Course.objects.filter(is_active=True)
    enrolled_ids = Enrollment.objects.filter(student=student).values_list('course_id', flat=True)

    if request.method == 'POST':
        selected_courses = request.POST.getlist('courses')
        enrolled_count = 0
        for course_id in selected_courses:
            try:
                course = Course.objects.get(pk=course_id)
                _, created = Enrollment.objects.get_or_create(student=student, course=course)
                if created:
                    enrolled_count += 1
            except Course.DoesNotExist:
                pass
        messages.success(request, f'Enrolled "{student.username}" in {enrolled_count} new course(s)!')
        return redirect('admin_student_list')

    return render(request, 'admin_panel/student_enroll.html', {
        'student': student,
        'courses': courses,
        'enrolled_ids': list(enrolled_ids),
    })


# ──────────────────────────────────────────────────────────
# COURSE MANAGEMENT (Admin-only creation)
# ──────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def admin_course_list(request):
    courses = Course.objects.select_related('department', 'teacher').annotate(
        student_count=Count('enrollments')
    ).order_by('-created_at')
    active_count = Course.objects.filter(is_active=True, approval_status='approved').count()
    inactive_count = Course.objects.filter(is_active=False).count() + Course.objects.filter(approval_status='rejected').count()
    return render(request, 'admin_panel/course_list.html', {
        'courses': courses,
        'active_count': active_count,
        'inactive_count': inactive_count
    })


@login_required
@user_passes_test(is_admin)
def admin_course_create(request):
    departments = Department.objects.filter(is_active=True)
    teachers = CustomUser.objects.filter(role='teacher', account_status='active')

    if request.method == 'POST':
        course_code = request.POST.get('course_code', '').strip().upper()
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        department_id = request.POST.get('department')
        teacher_id = request.POST.get('teacher')
        batch = request.POST.get('batch', '').strip()
        max_students = request.POST.get('max_students', 50)
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None
        cover_image = request.FILES.get('cover_image')

        if not title or not teacher_id:
            messages.error(request, 'Title and assigned teacher are required.')
            return render(request, 'admin_panel/course_form.html', {
                'form_data': request.POST, 'departments': departments,
                'teachers': teachers, 'is_edit': False
            })

        if course_code and Course.objects.filter(course_code=course_code).exists():
            messages.error(request, f'Course code "{course_code}" already exists.')
            return render(request, 'admin_panel/course_form.html', {
                'form_data': request.POST, 'departments': departments,
                'teachers': teachers, 'is_edit': False
            })

        course = Course.objects.create(
            course_code=course_code if course_code else None,
            title=title,
            description=description,
            department_id=department_id if department_id else None,
            teacher_id=teacher_id,
            batch=batch if batch else None,
            max_students=int(max_students) if max_students else 50,
            start_date=start_date,
            end_date=end_date,
            cover_image=cover_image,
            approval_status='approved',  # Admin-created courses are automatically approved
        )
        messages.success(request, f'Course "{course.title}" ({course.course_code}) created and assigned to teacher!')
        return redirect('admin_course_list')

    return render(request, 'admin_panel/course_form.html', {
        'departments': departments, 'teachers': teachers, 'is_edit': False
    })


@login_required
@user_passes_test(is_admin)
def admin_course_approve(request, pk):
    course = get_object_or_404(Course, pk=pk)
    course.approval_status = 'approved'
    course.save()
    messages.success(request, f'Course "{course.title}" has been approved!')
    return redirect('admin_course_list')


@login_required
@user_passes_test(is_admin)
def admin_course_reject(request, pk):
    course = get_object_or_404(Course, pk=pk)
    course.approval_status = 'rejected'
    course.save()
    messages.success(request, f'Course "{course.title}" has been rejected.')
    return redirect('admin_course_list')


@login_required
@user_passes_test(is_admin)
def admin_course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    departments = Department.objects.filter(is_active=True)
    teachers = CustomUser.objects.filter(role='teacher', account_status='active')

    if request.method == 'POST':
        course.course_code = request.POST.get('course_code', '').strip().upper() or None
        course.title = request.POST.get('title', '').strip()
        course.description = request.POST.get('description', '').strip()
        department_id = request.POST.get('department')
        course.department_id = department_id if department_id else None
        course.teacher_id = request.POST.get('teacher')
        course.batch = request.POST.get('batch', '').strip() or None
        course.max_students = int(request.POST.get('max_students', 50) or 50)
        course.start_date = request.POST.get('start_date') or None
        course.end_date = request.POST.get('end_date') or None
        course.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('cover_image'):
            course.cover_image = request.FILES.get('cover_image')

        if course.course_code and Course.objects.filter(course_code=course.course_code).exclude(pk=pk).exists():
            messages.error(request, f'Course code "{course.course_code}" already exists.')
            return render(request, 'admin_panel/course_form.html', {
                'course': course, 'departments': departments,
                'teachers': teachers, 'is_edit': True
            })

        course.save()
        messages.success(request, f'Course "{course.title}" updated.')
        return redirect('admin_course_list')

    return render(request, 'admin_panel/course_form.html', {
        'course': course, 'departments': departments,
        'teachers': teachers, 'is_edit': True
    })


# ──────────────────────────────────────────────────────────
# ADMIN CREATION
# ──────────────────────────────────────────────────────────
@login_required
def admin_create(request):
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, 'Permission denied.')
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        is_full_access = request.POST.get('is_full_access') == 'on'
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='admin',
                account_status='active',
                is_superuser=is_full_access
            )
            messages.success(request, f'Admin account {username} created successfully.')
            return redirect('admin_dashboard')
            
    return render(request, 'admin_panel/admin_create.html')

# ──────────────────────────────────────────────────────────
# SITE ADMINISTRATION (Django-admin-style model browser)
# ──────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def site_admin_view(request):
    """
    A beautiful custom Site Administration page showing all
    models grouped by app, with +Add and Change links to
    Django's built-in admin pages.
    """
    from django.apps import apps as django_apps

    # Define all apps and their models with metadata
    APP_REGISTRY = [
        {
            'name': 'Assignments',
            'icon': 'bi-file-earmark-text',
            'color': '#145af2',
            'gradient': 'linear-gradient(135deg, #0f3fae, #145af2)',
            'models': [
                {'label': 'Assignments',  'app': 'assignments', 'model': 'assignment'},
                {'label': 'Submissions',  'app': 'assignments', 'model': 'submission'},
            ],
        },
        {
            'name': 'Attendance',
            'icon': 'bi-calendar-check',
            'color': '#0d9f8c',
            'gradient': 'linear-gradient(135deg, #0b6a60, #0d9f8c)',
            'models': [
                {'label': 'Attendance Records',  'app': 'attendance', 'model': 'attendancerecord'},
                {'label': 'Attendance Sessions', 'app': 'attendance', 'model': 'attendancesession'},
            ],
        },
        {
            'name': 'Certificates',
            'icon': 'bi-award',
            'color': '#f59e0b',
            'gradient': 'linear-gradient(135deg, #d97706, #f59e0b)',
            'models': [
                {'label': 'Certificates', 'app': 'certificates', 'model': 'certificate'},
            ],
        },
        {
            'name': 'Chat',
            'icon': 'bi-chat-dots',
            'color': '#8b5cf6',
            'gradient': 'linear-gradient(135deg, #6d28d9, #8b5cf6)',
            'models': [
                {'label': 'Group Messages', 'app': 'chat', 'model': 'groupmessage'},
                {'label': 'Messages',        'app': 'chat', 'model': 'message'},
            ],
        },
        {
            'name': 'Courses',
            'icon': 'bi-journal-bookmark',
            'color': '#145af2',
            'gradient': 'linear-gradient(135deg, #0f3fae, #145af2)',
            'models': [
                {'label': 'Courses',     'app': 'courses', 'model': 'course'},
                {'label': 'Departments', 'app': 'courses', 'model': 'department'},
                {'label': 'Enrollments', 'app': 'courses', 'model': 'enrollment'},
            ],
        },
        {
            'name': 'Materials',
            'icon': 'bi-file-earmark-richtext',
            'color': '#ec4899',
            'gradient': 'linear-gradient(135deg, #be185d, #ec4899)',
            'models': [
                {'label': 'Materials', 'app': 'materials', 'model': 'material'},
            ],
        },
        {
            'name': 'Online Tests',
            'icon': 'bi-pencil-square',
            'color': '#f97316',
            'gradient': 'linear-gradient(135deg, #c2410c, #f97316)',
            'models': [
                {'label': 'Coding Test Cases',  'app': 'tests', 'model': 'codingtestcase'},
                {'label': 'Questions',          'app': 'tests', 'model': 'question'},
                {'label': 'Student Responses',  'app': 'tests', 'model': 'studentresponse'},
                {'label': 'Tests',              'app': 'tests', 'model': 'test'},
            ],
        },
        {
            'name': 'Projects',
            'icon': 'bi-folder2-open',
            'color': '#10b981',
            'gradient': 'linear-gradient(135deg, #065f46, #10b981)',
            'models': [
                {'label': 'Project Submissions', 'app': 'projects', 'model': 'projectsubmission'},
            ],
        },
        {
            'name': 'Quiz',
            'icon': 'bi-question-circle',
            'color': '#06b6d4',
            'gradient': 'linear-gradient(135deg, #0e7490, #06b6d4)',
            'models': [
                {'label': 'Quiz Attempts', 'app': 'quiz', 'model': 'quizattempt'},
                {'label': 'Quizzes',       'app': 'quiz', 'model': 'quiz'},
            ],
        },
        {
            'name': 'Recorded Classes',
            'icon': 'bi-play-btn',
            'color': '#d34767',
            'gradient': 'linear-gradient(135deg, #9f1239, #d34767)',
            'models': [
                {'label': 'Recorded Classes', 'app': 'recorded_classes', 'model': 'recordedclass'},
            ],
        },
        {
            'name': 'Reports',
            'icon': 'bi-bar-chart',
            'color': '#64748b',
            'gradient': 'linear-gradient(135deg, #334155, #64748b)',
            'models': [
                {'label': 'Reports', 'app': 'reports', 'model': 'reportcard'},
            ],
        },
        {
            'name': 'Users',
            'icon': 'bi-person-gear',
            'color': '#7c3aed',
            'gradient': 'linear-gradient(135deg, #4c1d95, #7c3aed)',
            'models': [
                {'label': 'Users', 'app': 'users', 'model': 'customuser'},
            ],
        },
    ]

    # Enrich each model with a live count
    for app in APP_REGISTRY:
        for model_entry in app['models']:
            try:
                model_cls = django_apps.get_model(model_entry['app'], model_entry['model'])
                model_entry['count'] = model_cls.objects.count()
            except Exception:
                model_entry['count'] = '—'

    return render(request, 'admin_panel/site_admin.html', {
        'app_registry': APP_REGISTRY,
    })


@login_required
@user_passes_test(is_admin)
def bulk_approve_users(request):
    """Bulk approve or reject selected student or teacher accounts."""
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')
        action = request.POST.get('action')
        
        if user_ids and action:
            users = CustomUser.objects.filter(pk__in=user_ids)
            if action == 'approve':
                updated_count = users.update(account_status='active')
                messages.success(request, f'Successfully approved {updated_count} user(s)!')
            elif action == 'reject':
                updated_count = users.update(account_status='rejected')
                messages.warning(request, f'Successfully rejected {updated_count} user(s).')
        else:
            messages.error(request, 'No users selected or action was unspecified.')
            
    referrer = request.META.get('HTTP_REFERER', 'admin_dashboard')
    return redirect(referrer)
