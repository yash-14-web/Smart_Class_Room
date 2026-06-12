from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Course, Enrollment
from .forms import CourseForm
from users.models import CustomUser

@login_required
def course_list(request):
    if request.user.is_teacher():
        courses = Course.objects.filter(teacher=request.user)
    else:
        all_courses = Course.objects.filter(is_active=True)
        enrolled_ids = Enrollment.objects.filter(student=request.user).values_list('course_id', flat=True)
        courses = all_courses
        context = {'courses': courses, 'enrolled_ids': list(enrolled_ids)}
        return render(request, 'courses/course_list.html', context)
    return render(request, 'courses/course_list.html', {'courses': courses})

@login_required
def course_create(request):
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can create courses.')
        return redirect('course_list')
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.save()
            messages.success(request, f'Course "{course.title}" created successfully!')
            return redirect('course_detail', pk=course.pk)
    else:
        form = CourseForm()
    return render(request, 'courses/course_form.html', {'form': form, 'title': 'Create Course'})

@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    is_enrolled = False
    if request.user.is_student():
        is_enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()
        if not is_enrolled and course.teacher != request.user:
            messages.error(request, 'You are not enrolled in this course.')
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

    students = Enrollment.objects.filter(course=course)
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'materials': materials,
        'assignments': assignments,
        'quizzes': quizzes,
        'tests': tests,
        'students': students,
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
    if not course.is_active:
        messages.error(request, 'Enrollment is not open for this course.')
        return redirect('course_list')

    is_enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()

    if request.method == 'POST':
        enrollment, created = Enrollment.objects.get_or_create(student=request.user, course=course)
        if created:
            messages.success(request, f'Successfully enrolled in "{course.title}"!')
        else:
            messages.info(request, 'You are already enrolled.')
        return redirect('course_detail', pk=pk)

    # GET request: Render the confirmation page
    from django.utils import timezone
    is_future = course.start_date and timezone.now() < course.start_date
    return render(request, 'courses/course_enroll_confirm.html', {
        'course': course,
        'already_enrolled': is_enrolled,
        'is_future': is_future,
    })

@login_required
def unenroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    Enrollment.objects.filter(student=request.user, course=course).delete()
    messages.success(request, f'Unenrolled from "{course.title}".')
    return redirect('course_list')


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
