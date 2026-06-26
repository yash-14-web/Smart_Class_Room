from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from .models import Course, Enrollment, Department, VirtualSession
from .forms import CourseForm, VirtualSessionForm
from users.models import CustomUser

@login_required
def course_list(request):
    # Both teachers and students see active departments first!
    if request.user.is_teacher():
        departments = Department.objects.filter(is_active=True).annotate(
            course_count=Count('courses', filter=Q(courses__teacher=request.user))
        )
    else:
        # Students only count approved courses in active departments
        departments = Department.objects.filter(is_active=True).annotate(
            course_count=Count('courses', filter=Q(courses__is_active=True, courses__approval_status='approved'))
        )
    return render(request, 'courses/course_list.html', {'departments': departments})

@login_required
def course_create(request):
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can create courses.')
        return redirect('course_list')
    
    dept_id = request.GET.get('department')
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.approval_status = 'pending'  # Teacher course starts as pending approval
            course.save()
            messages.success(request, f'Course "{course.title}" created successfully and is pending admin approval!')
            if course.department:
                return redirect('department_courses', dept_pk=course.department.pk)
            return redirect('course_list')
    else:
        initial_data = {}
        if dept_id:
            initial_data['department'] = dept_id
        form = CourseForm(initial=initial_data)
        
    return render(request, 'courses/course_form.html', {'form': form, 'title': 'Create Course', 'dept_id': dept_id})

@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    is_enrolled = False
    
    # Check if student enrollment is approved
    if request.user.is_student():
        is_enrolled = Enrollment.objects.filter(student=request.user, course=course, status='approved').exists()
        if not is_enrolled and course.teacher != request.user:
            messages.error(request, 'You are not enrolled in this course or your enrollment is pending approval.')
            return redirect('course_list')
            
    materials = course.materials.all()
    assignments = course.assignments.all()
    quizzes = course.quizzes.all()
    tests = course.tests.all()
    
    if request.user.is_student():
        from django.db.models import Q
        assignments = assignments.filter(
            Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
        ).distinct()
        quizzes = quizzes.filter(
            Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
        ).distinct()
        tests = tests.filter(
            Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
        ).distinct()

    students = Enrollment.objects.filter(course=course, status='approved').select_related('student')
    pending_enrollments = []
    if request.user.is_teacher() or request.user.is_superuser or request.user.role == 'admin':
        pending_enrollments = Enrollment.objects.filter(course=course, status='pending').select_related('student')

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'materials': materials,
        'assignments': assignments,
        'quizzes': quizzes,
        'tests': tests,
        'students': students,
        'pending_enrollments': pending_enrollments,
        'is_enrolled': is_enrolled,
        'course_status': course.status_label(),
        'course_available': course.is_available(),
    })

@login_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully!')
            return redirect('course_detail', pk=course.pk)
    else:
        form = CourseForm(instance=course)
    return render(request, 'courses/course_form.html', {'form': form, 'title': 'Edit Course'})

@login_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Course deleted.')
        return redirect('course_list')
    return render(request, 'courses/course_confirm_delete.html', {'course': course})

@login_required
def enroll_course(request, pk):
    if not request.user.is_student():
        messages.error(request, 'Only students can enroll.')
        return redirect('course_list')
    course = get_object_or_404(Course, pk=pk)
    if not course.is_active or course.approval_status != 'approved':
        messages.error(request, 'Enrollment is not open for this course.')
        return redirect('course_list')

    enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
    is_enrolled = enrollment is not None and enrollment.status == 'approved'
    is_pending = enrollment is not None and enrollment.status == 'pending'

    if request.method == 'POST':
        if enrollment:
            if enrollment.status == 'approved':
                messages.info(request, 'You are already enrolled.')
            elif enrollment.status == 'pending':
                messages.info(request, 'Your enrollment request is already pending approval.')
            else:
                # Re-apply
                enrollment.status = 'pending'
                enrollment.save()
                messages.success(request, f'Your request to join "{course.title}" has been submitted for approval!')
                from users.models import notify_user
                notify_user(course.teacher, "New Enrollment Request", f"Student {request.user.username} has requested to join your course '{course.title}'.", "enrollment")
        else:
            Enrollment.objects.create(student=request.user, course=course, status='pending')
            messages.success(request, f'Your request to join "{course.title}" has been submitted for approval!')
            from users.models import notify_user
            notify_user(course.teacher, "New Enrollment Request", f"Student {request.user.username} has requested to join your course '{course.title}'.", "enrollment")
        return redirect('course_list')

    # GET request: Render the confirmation page
    from django.utils import timezone
    is_future = course.start_date and timezone.now() < course.start_date
    return render(request, 'courses/course_enroll_confirm.html', {
        'course': course,
        'already_enrolled': is_enrolled,
        'is_pending': is_pending,
        'is_future': is_future,
    })

@login_required
def unenroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    Enrollment.objects.filter(student=request.user, course=course).delete()
    messages.success(request, f'Unenrolled/Cancelled request from "{course.title}".')
    return redirect('course_list')

@login_required
def approve_enrollment(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    # Check authorization (must be course teacher or admin)
    if not (request.user.is_superuser or request.user.role == 'admin' or enrollment.course.teacher == request.user):
        messages.error(request, 'You are not authorized to approve enrollments for this course.')
        return redirect('course_list')

    enrollment.status = 'approved'
    enrollment.save()
    from users.models import notify_user
    notify_user(enrollment.student, "Enrollment Approved", f"Your enrollment request for '{enrollment.course.title}' has been approved!", "enrollment")
    messages.success(request, f'Approved student "{enrollment.student.username}" for "{enrollment.course.title}"!')
    return redirect('course_detail', pk=enrollment.course.pk)

@login_required
def reject_enrollment(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    # Check authorization (must be course teacher or admin)
    if not (request.user.is_superuser or request.user.role == 'admin' or enrollment.course.teacher == request.user):
        messages.error(request, 'You are not authorized to reject enrollments for this course.')
        return redirect('course_list')

    enrollment.status = 'rejected'
    enrollment.save()
    from users.models import notify_user
    notify_user(enrollment.student, "Enrollment Rejected", f"Your enrollment request for '{enrollment.course.title}' has been rejected.", "enrollment")
    messages.success(request, f'Rejected enrollment request for student "{enrollment.student.username}".')
    return redirect('course_detail', pk=enrollment.course.pk)


@login_required
def get_course_students(request, course_id):
    from django.http import JsonResponse
    course = get_object_or_404(Course, pk=course_id)
    if not request.user.is_teacher() or course.teacher != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    enrollments = Enrollment.objects.filter(course=course).select_related('student')
    students = []
    for enrollment in enrollments:
        student = enrollment.student
        students.append({
            'id': student.id,
            'username': student.username,
            'full_name': student.get_full_name() or student.username,
        })
    return JsonResponse({'students': students})


@login_required
def department_courses(request, dept_pk):
    department = get_object_or_404(Department, pk=dept_pk, is_active=True)
    if request.user.is_teacher():
        courses = Course.objects.filter(department=department, teacher=request.user)
    else:
        # Students see approved active courses in this department
        all_courses = Course.objects.filter(department=department, is_active=True, approval_status='approved')
        enrollments = Enrollment.objects.filter(student=request.user)
        enrollment_dict = {e.course_id: e.status for e in enrollments}
        for course in all_courses:
            course.enrollment_status = enrollment_dict.get(course.pk, None)
        courses = all_courses

    return render(request, 'courses/department_courses.html', {
        'department': department,
        'courses': courses,
    })


@login_required
def create_virtual_session(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if not (request.user.is_teacher() and course.teacher == request.user):
        messages.error(request, "Only the course teacher can schedule virtual sessions.")
        return redirect('course_detail', pk=course.pk)

    if request.method == 'POST':
        form = VirtualSessionForm(request.POST)
        if form.is_valid():
            virtual_session = form.save(commit=False)
            virtual_session.course = course
            virtual_session.save()

            # Create or open an Attendance Session automatically for the session date
            from attendance.models import AttendanceSession
            session_date = virtual_session.scheduled_at.date()
            attendance_session, created = AttendanceSession.objects.get_or_create(
                course=course,
                date=session_date,
                defaults={
                    'topic': f"Virtual Session: {virtual_session.title}",
                    'is_open': True,
                    'created_by': request.user
                }
            )
            if not created:
                attendance_session.is_open = True
                attendance_session.topic = f"Virtual Session: {virtual_session.title}"
                attendance_session.save()

            messages.success(request, f"Virtual session '{virtual_session.title}' scheduled and attendance session is open for {session_date}!")
            return redirect('course_detail', pk=course.pk)
    else:
        form = VirtualSessionForm()
    return render(request, 'courses/create_virtual_session.html', {'form': form, 'course': course})


@login_required
def ai_tutor_view(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    
    # Must be teacher of this course or approved student
    is_teacher = course.teacher == request.user
    is_student_enrolled = Enrollment.objects.filter(student=request.user, course=course, status='approved').exists()
    
    if not (is_teacher or is_student_enrolled):
        messages.error(request, "You do not have access to this course's AI Tutor.")
        return redirect('course_list')

    from django.http import JsonResponse
    from .models import AITutorMessage

    if request.method == 'POST':
        action = request.POST.get('action', 'general')
        topic = request.POST.get('topic', '').strip()
        context = request.POST.get('context', '').strip()
        
        user_role = 'teacher' if request.user.is_teacher() else 'student'
        
        if not topic:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Topic/message cannot be empty'}, status=400)
            messages.error(request, 'Please enter a topic or message.')
            return redirect('ai_tutor_view', course_pk=course.pk)
            
        # Save user query
        AITutorMessage.objects.create(
            course=course,
            user=request.user,
            sender='user',
            action=action,
            text=topic
        )

        from .ai_tutor import generate_ai_response, get_gemini_api_key
        
        ai_response = generate_ai_response(user_role, action, topic, context)
        
        # Save AI response
        AITutorMessage.objects.create(
            course=course,
            user=request.user,
            sender='ai',
            action=action,
            text=ai_response
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'response': ai_response,
                'is_demo': get_gemini_api_key() is None
            })
            
        chat_history = AITutorMessage.objects.filter(course=course, user=request.user).order_by('timestamp')
        return render(request, 'courses/ai_tutor.html', {
            'course': course,
            'response': ai_response,
            'topic': topic,
            'action': action,
            'context_val': context,
            'is_demo': get_gemini_api_key() is None,
            'chat_history': chat_history
        })
        
    from .ai_tutor import get_gemini_api_key
    chat_history = AITutorMessage.objects.filter(course=course, user=request.user).order_by('timestamp')
    return render(request, 'courses/ai_tutor.html', {
        'course': course,
        'is_demo': get_gemini_api_key() is None,
        'chat_history': chat_history
    })

@login_required
def course_about(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, 'courses/course_about.html', {'course': course})

