from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.db.models import Sum, Avg
from django.utils import timezone
from datetime import timedelta
import json
from .forms import RegisterForm, LoginForm, ProfileUpdateForm
from courses.models import Course, Enrollment
from assignments.models import Assignment, Submission
from projects.models import ProjectSubmission


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.username}!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    user = request.user
    if user.is_teacher():
        from attendance.models import AttendanceRecord
        from quiz.models import Quiz

        courses = list(
            Course.objects.filter(teacher=user).order_by('-created_at')
        )
        total_students = Enrollment.objects.filter(course__teacher=user).count()
        total_assignments = Assignment.objects.filter(course__teacher=user).count()
        total_quizzes = Quiz.objects.filter(course__teacher=user).count()
        
        pending_assignments = Submission.objects.filter(
            assignment__course__teacher=user, grade__isnull=True
        ).count()
        graded_assignments = Submission.objects.filter(
            assignment__course__teacher=user,
            grade__isnull=False,
        ).count()

        pending_projects = ProjectSubmission.objects.filter(
            course__teacher=user, score__isnull=True
        ).count()
        graded_projects = ProjectSubmission.objects.filter(
            course__teacher=user, score__isnull=False
        ).count()

        pending_submissions = pending_assignments + pending_projects
        graded_submissions = graded_assignments + graded_projects

        attendance_records = AttendanceRecord.objects.filter(
            session__course__teacher=user
        )
        attendance_present = attendance_records.filter(status='present').count()
        attendance_absent = attendance_records.filter(status='absent').count()
        attendance_rate = round(
            (attendance_present / attendance_records.count()) * 100, 1
        ) if attendance_records.exists() else 0

        teacher_course_labels = []
        teacher_student_counts = []
        teacher_assignment_counts = []
        teacher_quiz_counts = []
        teacher_pending_review_counts = []
        active_courses = 0
        results_released_courses = 0

        for course in courses:
            student_total = course.enrollments.count()
            assignment_total = course.assignments.count()
            quiz_total = course.quizzes.count()
            pending_review_total = Submission.objects.filter(
                assignment__course=course,
                grade__isnull=True,
            ).count() + ProjectSubmission.objects.filter(
                course=course,
                score__isnull=True,
            ).count()

            course.student_total = student_total
            course.assignment_total = assignment_total
            course.quiz_total = quiz_total
            course.pending_review_total = pending_review_total
            course.status_display = course.status_label()

            teacher_course_labels.append(course.title)
            teacher_student_counts.append(student_total)
            teacher_assignment_counts.append(assignment_total)
            teacher_quiz_counts.append(quiz_total)
            teacher_pending_review_counts.append(pending_review_total)

            if course.is_active:
                active_courses += 1
            if course.results_released:
                results_released_courses += 1

        inactive_courses = len(courses) - active_courses
        review_completion_rate = round(
            (graded_submissions / (graded_submissions + pending_submissions)) * 100, 1
        ) if (graded_submissions + pending_submissions) else 0

        # Fetch actual pending submissions to grade (assignments & projects)
        pending_review_list = []
        unmarked_assignments = Submission.objects.filter(
            assignment__course__teacher=user,
            grade__isnull=True
        ).select_related('assignment', 'student', 'assignment__course').order_by('submitted_at')[:5]
        
        for sub in unmarked_assignments:
            pending_review_list.append({
                'title': sub.assignment.title,
                'student': sub.student.get_full_name() or sub.student.username,
                'course': sub.assignment.course.title,
                'type': sub.assignment.get_label_display(),
                'submitted_at': sub.submitted_at,
                'url_name': 'grade_submission',
                'url_arg': sub.pk,
            })

        unmarked_projects = ProjectSubmission.objects.filter(
            course__teacher=user,
            score__isnull=True
        ).select_related('student', 'course').order_by('submitted_at')[:5]

        for sub in unmarked_projects:
            pending_review_list.append({
                'title': sub.title or 'Project Submission',
                'student': sub.student.get_full_name() or sub.student.username,
                'course': sub.course.title,
                'type': 'Project',
                'submitted_at': sub.submitted_at,
                'url_name': 'project_detail',
                'url_arg': sub.pk,
            })

        pending_review_list.sort(key=lambda x: x['submitted_at'] if x['submitted_at'] else timezone.now())
        pending_review_list = pending_review_list[:5]

        context = {
            'courses':                       courses,
            'pending_review_list':           pending_review_list,
            'total_students':                total_students,
            'total_assignments':             total_assignments,
            'total_quizzes':                 total_quizzes,
            'pending_submissions':           pending_submissions,
            'graded_submissions':            graded_submissions,
            'attendance_rate':               attendance_rate,
            'attendance_present':            attendance_present,
            'attendance_absent':             attendance_absent,
            'active_courses':                active_courses,
            'inactive_courses':              inactive_courses,
            'results_released_courses':      results_released_courses,
            'review_completion_rate':        review_completion_rate,
            'teacher_course_labels':         json.dumps(teacher_course_labels),
            'teacher_student_counts':        json.dumps(teacher_student_counts),
            'teacher_assignment_counts':     json.dumps(teacher_assignment_counts),
            'teacher_quiz_counts':           json.dumps(teacher_quiz_counts),
            'teacher_pending_review_counts': json.dumps(teacher_pending_review_counts),
            'teacher_submission_breakdown':  json.dumps([
                graded_submissions,
                pending_submissions,
            ]),
            'teacher_attendance_breakdown':  json.dumps([
                attendance_present,
                attendance_absent,
            ]),
        }
    else:
        from quiz.models import Quiz, QuizAttempt
        from attendance.models import AttendanceRecord
        from tests.models import Test, StudentResponse
        from django.db.models import Q

        enrollments = Enrollment.objects.filter(student=user).select_related(
            'course', 'course__teacher'
        )
        courses = [e.course for e in enrollments]
        now = timezone.now()

        assignment_qs = Assignment.objects.filter(course__in=courses).filter(
            Q(assigned_to=user) | Q(assigned_to__isnull=True)
        ).distinct()
        active_assignments = assignment_qs.filter(due_date__gte=now)
        pending_assignments = active_assignments.exclude(
            submissions__student=user
        ).count()
        missed_assignments = list(
            assignment_qs.filter(due_date__lt=now).exclude(submissions__student=user)
        )

        quiz_qs = Quiz.objects.filter(
            course__in=courses,
            is_active=True,
        ).filter(
            Q(assigned_to=user) | Q(assigned_to__isnull=True)
        ).distinct()
        active_quizzes = quiz_qs.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now)
        ).filter(
            Q(due_date__isnull=True) | Q(due_date__gte=now)
        )
        pending_quizzes = active_quizzes.exclude(
            attempts__student=user,
            attempts__is_complete=True,
        ).count()
        missed_quizzes = list(
            quiz_qs.filter(due_date__lt=now).exclude(
                attempts__student=user,
                attempts__is_complete=True,
            )
        )

        test_qs = Test.objects.filter(course__in=courses, is_active=True).filter(
            Q(assigned_to=user) | Q(assigned_to__isnull=True)
        ).distinct()
        active_tests = test_qs.filter(available_from__lte=now).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )
        pending_tests = active_tests.exclude(responses__student=user).count()
        missed_tests = list(
            test_qs.filter(end_date__lt=now).exclude(responses__student=user)
        )

        today = timezone.localdate()
        week_dates = [today - timedelta(days=day) for day in range(6, -1, -1)]
        weekly_labels = [d.strftime('%a') for d in week_dates]
        weekly_assignment_completed = []
        weekly_quiz_completed = []
        weekly_test_completed = []
        weekly_project_completed = []

        for day in week_dates:
            weekly_assignment_completed.append(
                Submission.objects.filter(
                    student=user,
                    submitted_at__date=day,
                ).count()
            )
            weekly_quiz_completed.append(
                QuizAttempt.objects.filter(
                    student=user,
                    is_complete=True,
                    finished_at__date=day,
                ).count()
            )
            weekly_test_completed.append(
                StudentResponse.objects.filter(
                    student=user,
                    submitted_at__date=day,
                ).count()
            )
            weekly_project_completed.append(
                ProjectSubmission.objects.filter(
                    student=user,
                    submitted_at__date=day,
                ).count()
            )

        completed_assignments = Submission.objects.filter(
            student=user,
            assignment__in=assignment_qs,
        ).count()
        total_assignments = assignment_qs.count()
        completed_quizzes = QuizAttempt.objects.filter(
            student=user,
            quiz__in=quiz_qs,
            is_complete=True,
        ).count()
        total_quizzes = quiz_qs.count()
        completed_tests = StudentResponse.objects.filter(
            student=user,
            test__in=test_qs,
        ).count()
        total_tests = test_qs.count()

        completed_projects = ProjectSubmission.objects.filter(
            student=user,
            course__in=courses,
        ).count()
        pending_projects = 0
        for course in courses:
            if course.is_project_submission_open():
                if not ProjectSubmission.objects.filter(student=user, course=course).exists():
                    pending_projects += 1

        total_pending_work = pending_assignments + pending_quizzes + pending_tests + pending_projects

        graded_assignment_subs = Submission.objects.filter(
            student=user,
            assignment__course__in=courses,
            grade__isnull=False,
        ).select_related('assignment')
        assignment_scored = sum(sub.grade or 0 for sub in graded_assignment_subs)
        assignment_total = sum(sub.assignment.total_marks for sub in graded_assignment_subs)
        assignment_total += sum(assignment.total_marks for assignment in missed_assignments)

        completed_quiz_attempts = QuizAttempt.objects.filter(
            student=user,
            quiz__course__in=courses,
            is_complete=True,
        ).select_related('quiz')
        quiz_scored = sum(attempt.score for attempt in completed_quiz_attempts)
        quiz_total = sum(attempt.quiz.total_marks for attempt in completed_quiz_attempts)
        quiz_total += sum(quiz.total_marks for quiz in missed_quizzes)

        completed_test_responses = StudentResponse.objects.filter(
            student=user,
            test__course__in=courses,
        ).select_related('test')
        test_scored = sum(response.score for response in completed_test_responses)
        test_total = sum(response.test.total_marks for response in completed_test_responses)
        test_total += sum(test.total_marks for test in missed_tests)

        graded_projects = ProjectSubmission.objects.filter(
            student=user,
            course__in=courses,
            score__isnull=False,
        )
        project_scored = sum(project.score or 0 for project in graded_projects)
        project_total = sum(project.total_marks for project in graded_projects)

        overall_scored = assignment_scored + quiz_scored + test_scored + project_scored
        overall_total = assignment_total + quiz_total + test_total + project_total
        overall_performance = round(
            (overall_scored / overall_total) * 100, 1
        ) if overall_total else 0

        attendance_records = AttendanceRecord.objects.filter(
            student=user,
            session__course__in=courses,
        )
        attendance_total = attendance_records.count()
        attendance_present = attendance_records.filter(status='present').count()
        attendance_percentage = round(
            (attendance_present / attendance_total) * 100, 1
        ) if attendance_total else 0

        upcoming_assignments = list(
            assignment_qs.filter(
                due_date__gte=now,
            ).exclude(
                submissions__student=user,
            ).select_related('course').order_by('due_date')[:3]
        )
        upcoming_quizzes = list(
            active_quizzes.exclude(
                attempts__student=user,
                attempts__is_complete=True,
            ).select_related('course').order_by('due_date', 'created_at')[:3]
        )
        upcoming_tests = list(
            active_tests.exclude(
                responses__student=user,
            ).select_related('course').order_by('end_date', 'available_from')[:3]
        )

        upcoming_items = []
        for assignment in upcoming_assignments:
            upcoming_items.append({
                'title': assignment.title,
                'course': assignment.course.title,
                'type': assignment.get_label_display(),
                'due_date': assignment.due_date,
                'url_name': 'assignment_detail',
                'url_arg': assignment.pk,
            })
        for quiz in upcoming_quizzes:
            upcoming_items.append({
                'title': quiz.title,
                'course': quiz.course.title,
                'type': 'Quiz',
                'due_date': quiz.due_date,
                'url_name': 'quiz_attempt',
                'url_arg': quiz.pk,
            })
        for test in upcoming_tests:
            upcoming_items.append({
                'title': test.title,
                'course': test.course.title if test.course else 'General Test',
                'type': 'Test',
                'due_date': test.end_date,
                'url_name': 'test_take',
                'url_arg': test.pk,
            })
        for course in courses:
            if course.is_project_submission_open():
                if not ProjectSubmission.objects.filter(student=user, course=course).exists():
                    upcoming_items.append({
                        'title': 'Project Submission',
                        'course': course.title,
                        'type': 'Project',
                        'due_date': course.project_end_date,
                        'url_name': 'project_submit',
                        'url_arg': None,
                    })
        upcoming_items.sort(
            key=lambda item: item['due_date'] or now + timedelta(days=3650)
        )
        upcoming_items = upcoming_items[:4]

        course_performance_labels = []
        course_performance_values = []
        course_attendance_values = []
        for course in courses:
            course_assignment_subs = [
                sub for sub in graded_assignment_subs if sub.assignment.course_id == course.pk
            ]
            course_assignment_scored = sum(sub.grade or 0 for sub in course_assignment_subs)
            course_assignment_total = sum(sub.assignment.total_marks for sub in course_assignment_subs)

            course_quiz_attempts = [
                attempt for attempt in completed_quiz_attempts if attempt.quiz.course_id == course.pk
            ]
            course_quiz_scored = sum(attempt.score for attempt in course_quiz_attempts)
            course_quiz_total = sum(attempt.quiz.total_marks for attempt in course_quiz_attempts)
            course_quiz_total += sum(
                quiz.total_marks for quiz in missed_quizzes if quiz.course_id == course.pk
            )

            course_test_responses = [
                response for response in completed_test_responses if response.test.course_id == course.pk
            ]
            course_test_scored = sum(response.score for response in course_test_responses)
            course_test_total = sum(response.test.total_marks for response in course_test_responses)
            course_test_total += sum(
                test.total_marks for test in missed_tests if test.course_id == course.pk
            )

            course_project_subs = [
                project for project in graded_projects if project.course_id == course.pk
            ]
            course_project_scored = sum(project.score or 0 for project in course_project_subs)
            course_project_total = sum(project.total_marks for project in course_project_subs)

            course_total_scored = (
                course_assignment_scored + course_quiz_scored + course_test_scored + course_project_scored
            )
            course_total_possible = (
                course_assignment_total + course_quiz_total + course_test_total + course_project_total
            )
            course_performance = round(
                (course_total_scored / course_total_possible) * 100, 1
            ) if course_total_possible else 0

            course_attendance_records = attendance_records.filter(session__course=course)
            course_attendance_total = course_attendance_records.count()
            course_attendance_present = course_attendance_records.filter(status='present').count()
            course_attendance = round(
                (course_attendance_present / course_attendance_total) * 100, 1
            ) if course_attendance_total else 0

            course_performance_labels.append(course.title)
            course_performance_values.append(course_performance)
            course_attendance_values.append(course_attendance)

        workload_breakdown = [
            completed_assignments,
            pending_assignments,
            completed_quizzes,
            pending_quizzes,
            completed_tests,
            pending_tests,
            completed_projects,
            pending_projects,
        ]

        context = {
            'enrollments':                  enrollments,
            'courses':                      courses,
            'pending_assignments':          pending_assignments,
            'pending_quizzes':              pending_quizzes,
            'pending_tests':                pending_tests,
            'pending_projects':             pending_projects,
            'completed_assignments':        completed_assignments,
            'completed_quizzes':            completed_quizzes,
            'completed_tests':              completed_tests,
            'completed_projects':           completed_projects,
            'total_assignments':            total_assignments,
            'total_quizzes':                total_quizzes,
            'total_tests':                  total_tests,
            'total_pending_work':           total_pending_work,
            'overall_performance':          overall_performance,
            'attendance_percentage':        attendance_percentage,
            'student_rank':                 _get_student_rank(user),
            'upcoming_items':               upcoming_items,
            'weekly_labels':                json.dumps(weekly_labels),
            'weekly_assignment_completed':  json.dumps(weekly_assignment_completed),
            'weekly_quiz_completed':        json.dumps(weekly_quiz_completed),
            'weekly_test_completed':        json.dumps(weekly_test_completed),
            'weekly_project_completed':     json.dumps(weekly_project_completed),
            'course_performance_labels':    json.dumps(course_performance_labels),
            'course_performance_values':    json.dumps(course_performance_values),
            'course_attendance_values':     json.dumps(course_attendance_values),
            'workload_breakdown':           json.dumps(workload_breakdown),
        }
    return render(request, 'users/dashboard.html', context)


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            if form.cleaned_data.get('remove_profile_pic') and user.profile_pic:
                user.profile_pic.delete(save=False)
                user.profile_pic = None
            user.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    certificates = []
    if request.user.is_student():
        from certificates.models import Certificate
        certificates = Certificate.objects.filter(student=request.user).select_related('course')

    return render(request, 'users/profile.html', {
        'form': form,
        'certificates': certificates,
    })


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control'
    return render(request, 'users/change_password.html', {'form': form})


@login_required
def leaderboard_view(request):
    from users.models import CustomUser
    from quiz.models import QuizAttempt
    from tests.models import StudentResponse
    course_id       = request.GET.get('course')
    courses         = Course.objects.filter(is_active=True)
    selected_course = None
    students        = CustomUser.objects.filter(role='student')

    def build_board(extra_filter):
        board = []
        for student in students:
            subs = Submission.objects.filter(
                student=student, grade__isnull=False, **extra_filter
            )
            total_assignment_marks = subs.aggregate(t=Sum('grade'))['t'] or 0
            assignment_count = subs.count()
            assignment_avg = subs.aggregate(a=Avg('grade'))['a'] or 0
            pending = Submission.objects.filter(
                student=student, grade__isnull=True, **extra_filter
            ).count()

            quiz_filter = {'student': student, 'is_complete': True}
            if 'assignment__course' in extra_filter:
                quiz_filter['quiz__course'] = extra_filter['assignment__course']

            quiz_attempts = QuizAttempt.objects.filter(**quiz_filter)
            total_quiz_marks = quiz_attempts.aggregate(t=Sum('score'))['t'] or 0
            quiz_count = quiz_attempts.count()
            quiz_avg = quiz_attempts.aggregate(a=Avg('score'))['a'] or 0

            test_filter = {'student': student}
            if 'assignment__course' in extra_filter:
                test_filter['test__course'] = extra_filter['assignment__course']

            test_responses = StudentResponse.objects.filter(**test_filter)
            total_test_marks = test_responses.aggregate(t=Sum('score'))['t'] or 0
            test_count = test_responses.count()
            test_avg = test_responses.aggregate(a=Avg('score'))['a'] or 0

            completed = assignment_count + quiz_count + test_count
            total_marks = total_assignment_marks + total_quiz_marks + total_test_marks
            avg_score = 0
            if completed:
                avg_score = round(
                    (
                        assignment_avg * assignment_count
                        + quiz_avg * quiz_count
                        + test_avg * test_count
                    ) / completed,
                    1
                )

            if completed or pending:
                if selected_course:
                    course_name = selected_course.title
                else:
                    course_count = Enrollment.objects.filter(student=student).count()
                    course_name = (
                        f'Across {course_count} courses'
                        if course_count else 'All Courses'
                    )

                board.append({
                    'student':            student,
                    'total_marks':        total_marks,
                    'completed':          completed,
                    'pending':            pending,
                    'avg_score':          avg_score,
                    'course_name':        course_name,
                    'submission_status':  'Completed' if pending == 0 else 'In Progress',
                })
        board.sort(
            key=lambda x: (x['total_marks'], x['avg_score'], x['completed']),
            reverse=True
        )
        for i, e in enumerate(board, 1):
            e['rank'] = i
        return board

    if course_id:
        selected_course = get_object_or_404(Course, pk=course_id)
        leaderboard     = build_board({'assignment__course': selected_course})
    else:
        leaderboard     = build_board({})

    my_rank = None
    if request.user.is_student():
        for e in leaderboard:
            if e['student'] == request.user:
                my_rank = e['rank']
                break

    return render(request, 'leaderboard/leaderboard.html', {
        'leaderboard':     leaderboard,
        'my_rank':         my_rank,
        'courses':         courses,
        'selected_course': selected_course,
    })


def _get_student_rank(student):
    """Calculate leaderboard rank for a student across all courses."""
    from users.models import CustomUser
    from quiz.models import QuizAttempt
    from tests.models import StudentResponse
    all_students = CustomUser.objects.filter(role='student')
    scores = []
    for s in all_students:
        assignment_total = Submission.objects.filter(
            student=s, grade__isnull=False
        ).aggregate(t=Sum('grade'))['t'] or 0
        quiz_total = QuizAttempt.objects.filter(
            student=s, is_complete=True
        ).aggregate(t=Sum('score'))['t'] or 0
        test_total = StudentResponse.objects.filter(
            student=s
        ).aggregate(t=Sum('score'))['t'] or 0
        total = assignment_total + quiz_total + test_total
        scores.append((s.pk, total))
    scores.sort(key=lambda x: x[1], reverse=True)
    for i, (pk, _) in enumerate(scores, 1):
        if pk == student.pk:
            return i
    return None


def _build_report(student, viewer=None):
    from quiz.models import Quiz, QuizAttempt
    from tests.models import Test, StudentResponse

    enrollments  = Enrollment.objects.filter(
        student=student
    ).select_related('course', 'course__teacher')
    joined_at = enrollments.order_by('enrolled_at').values_list(
        'enrolled_at', flat=True
    ).first()

    courses_data      = []
    grand_total_marks = 0
    grand_obtained    = 0
    grand_count       = 0
    viewer_is_teacher = bool(
        viewer and hasattr(viewer, 'is_teacher') and viewer.is_teacher()
    )
    viewer_is_owner = viewer == student

    for enrollment in enrollments:
        course      = enrollment.course
        assignments = Assignment.objects.filter(
            course=course
        ).order_by('label', 'created_at')

        rows          = []
        course_total  = 0
        course_scored = 0
        course_count  = 0

        for assignment in assignments:
            sub = Submission.objects.filter(
                student=student, assignment=assignment
            ).first()

            if sub and sub.grade is not None:
                score          = sub.grade
                avg_pct        = sub.percentage()
                status         = 'Graded'
                pass_fail      = 'Pass' if avg_pct >= 40 else 'Fail'
                course_total  += assignment.total_marks
                course_scored += score
                course_count  += 1
                grand_total_marks += assignment.total_marks
                grand_obtained    += score
                grand_count       += 1
            elif sub:
                score     = None
                avg_pct   = None
                status    = 'Submitted — Pending'
                pass_fail = 'Pending'
            else:
                score     = 0
                avg_pct   = 0
                status    = 'Not Submitted'
                pass_fail = 'Fail'
                course_total += assignment.total_marks
                course_count += 1
                grand_total_marks += assignment.total_marks
                grand_count += 1

            rows.append({
                'assignment':  assignment,
                'label':       assignment.get_label_display(),
                'total_marks': assignment.total_marks,
                'score':       score,
                'avg_pct':     avg_pct,
                'status':      status,
                'pass_fail':   pass_fail,
            })

        # Quiz rows
        quizzes = Quiz.objects.filter(course=course).order_by('created_at')
        attempts_by_quiz = {
            attempt.quiz_id: attempt
            for attempt in QuizAttempt.objects.filter(
                student=student,
                quiz__course=course,
                is_complete=True,
            ).select_related('quiz')
        }

        for quiz in quizzes:
            attempt = attempts_by_quiz.get(quiz.pk)
            if attempt:
                score = attempt.score
                avg_pct = attempt.percentage()
                status = 'Graded'
                pass_fail = 'Pass' if avg_pct >= 40 else 'Fail'
                course_scored += score
                grand_obtained += score
            else:
                score = 0
                avg_pct = 0
                status = 'Not Attempted'
                pass_fail = 'Fail'

            rows.append({
                'assignment':  quiz,
                'label':       'Quiz',
                'total_marks': quiz.total_marks,
                'score':       score,
                'avg_pct':     avg_pct,
                'status':      status,
                'pass_fail':   pass_fail,
            })
            course_total += quiz.total_marks
            course_count += 1
            grand_total_marks += quiz.total_marks
            grand_count += 1

        # Test rows
        tests = Test.objects.filter(course=course).order_by('created_at')
        responses_by_test = {
            response.test_id: response
            for response in StudentResponse.objects.filter(
                student=student,
                test__course=course,
            ).select_related('test')
        }

        for test in tests:
            response = responses_by_test.get(test.pk)
            if response:
                score = response.score
                avg_pct = round((response.score / test.total_marks) * 100, 1) if test.total_marks else 0
                status = 'Graded'
                pass_fail = 'Pass' if avg_pct >= 40 else 'Fail'
                course_scored += score
                grand_obtained += score
            elif test.end_date and test.end_date < timezone.now():
                score = 0
                avg_pct = 0
                status = 'Missed'
                pass_fail = 'Fail'
            else:
                score = None
                avg_pct = None
                status = 'Open'
                pass_fail = 'Pending'

            rows.append({
                'assignment':  test,
                'label':       'Test',
                'total_marks': test.total_marks,
                'score':       score,
                'avg_pct':     avg_pct,
                'status':      status,
                'pass_fail':   pass_fail,
            })
            course_total += test.total_marks
            course_count += 1
            grand_total_marks += test.total_marks
            grand_count += 1

        # Project rows
        project_submissions = ProjectSubmission.objects.filter(
            student=student, course=course
        ).order_by('submitted_at')

        for project in project_submissions:
            if project.score is not None:
                pct = round(
                    (project.score / project.total_marks) * 100, 1
                ) if project.total_marks else 0
                status = 'Graded'
                pass_fail = 'Pass' if pct >= 40 else 'Fail'
                course_total += project.total_marks
                course_scored += project.score
                course_count += 1
                grand_total_marks += project.total_marks
                grand_obtained += project.score
                grand_count += 1
                score = project.score
                avg_pct = pct
            else:
                score = None
                avg_pct = None
                status = 'Submitted - Pending'
                pass_fail = 'Pending'

            rows.append({
                'assignment':  project,
                'label':       'Project',
                'total_marks': project.total_marks,
                'score':       score,
                'avg_pct':     avg_pct,
                'status':      status,
                'pass_fail':   pass_fail,
            })

        course_avg  = round((course_scored / course_total * 100), 1) if course_total else 0
        course_pass = 'Pass' if course_avg >= 40 else ('Pending' if course_count == 0 else 'Fail')
        results_visible = (
            viewer_is_teacher or not viewer_is_owner or course.results_visible()
        )

        courses_data.append({
            'course':          course,
            'teacher':         course.teacher,
            'rows':            rows,
            'course_total':    course_total,
            'course_scored':   course_scored,
            'course_avg':      course_avg,
            'course_pass':     course_pass,
            'results_visible': results_visible,
        })

    grand_avg  = round((grand_obtained / grand_total_marks * 100), 1) if grand_total_marks else 0
    grand_pass = 'Pass' if grand_avg >= 40 else ('Pending' if grand_count == 0 else 'Fail')
    grand_results_visible = all(
        item['results_visible'] for item in courses_data
    ) if courses_data else True

    return {
        'student':               student,
        'courses_data':          courses_data,
        'grand_total_marks':     grand_total_marks,
        'grand_obtained':        grand_obtained,
        'grand_avg':             grand_avg,
        'grand_pass':            grand_pass,
        'grand_results_visible': grand_results_visible,
        'rank':                  _get_student_rank(student),
        'joined_at':             joined_at,
    }


@login_required
def report_card_view(request):
    student_id = request.GET.get('student')
    if student_id and request.user.is_teacher():
        from users.models import CustomUser
        student = get_object_or_404(CustomUser, pk=student_id)
    else:
        student = request.user

    data = _build_report(student, viewer=request.user)
    return render(request, 'users/report_card.html', {
        **data,
        'is_own_report': (student == request.user),
    })


@login_required
def download_report_pdf(request):
    student_id = request.GET.get('student')
    if student_id and request.user.is_teacher():
        from users.models import CustomUser
        student = get_object_or_404(CustomUser, pk=student_id)
    else:
        student = request.user

    data = _build_report(student, viewer=request.user)
    return render(request, 'users/report_card_print.html', {
        **data,
        'is_own_report': (student == request.user),
        'is_print': True,
        'auto_print': True,
    })
