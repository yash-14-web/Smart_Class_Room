from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import AttendanceSession, AttendanceRecord
from courses.models import Course, Enrollment
from users.models import CustomUser


# ── TEACHER: View all attendance sessions for a course ────────
@login_required
def attendance_list(request, course_pk):
    course   = get_object_or_404(Course, pk=course_pk)
    is_teacher = (course.teacher == request.user)

    if not is_teacher:
        # Student view — show own attendance summary
        return redirect('student_attendance', course_pk=course_pk)

    sessions = AttendanceSession.objects.filter(
        course=course
    ).prefetch_related('records')

    return render(request, 'attendance/attendance_list.html', {
        'course':   course,
        'sessions': sessions,
    })


# ── TEACHER: Create a new attendance session ──────────────────
@login_required
def create_session(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, teacher=request.user)

    if request.method == 'POST':
        date       = request.POST.get('date', timezone.localdate())
        topic      = request.POST.get('topic', '')
        allow_self = request.POST.get('allow_self') == 'on'

        # Prevent duplicate session on same date
        session, created = AttendanceSession.objects.get_or_create(
            course=course, date=date,
            defaults={
                'topic':      topic,
                'is_open':    allow_self,
                'created_by': request.user,
            }
        )
        if not created:
            messages.warning(request, f'Session for {date} already exists.')
            return redirect('take_attendance', session_pk=session.pk)

        # Auto-create absent records for all enrolled students
        enrollments = Enrollment.objects.filter(course=course, status='approved')
        for enrollment in enrollments:
            AttendanceRecord.objects.get_or_create(
                session=session,
                student=enrollment.student,
                defaults={'status': 'absent', 'marked_by': 'teacher'}
            )

        messages.success(
            request,
            f'Attendance session created for {date}!'
            + (' Students can now mark themselves.' if allow_self else '')
        )
        return redirect('take_attendance', session_pk=session.pk)

    return render(request, 'attendance/create_session.html', {'course': course})


# ── TEACHER: Mark / edit attendance for a session ─────────────
@login_required
def take_attendance(request, session_pk):
    session = get_object_or_404(
        AttendanceSession, pk=session_pk,
        course__teacher=request.user
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'toggle_open':
            session.is_open = not session.is_open
            if not session.is_open:
                session.closed_at = timezone.now()
            session.save()
            status = 'opened for self-marking' if session.is_open else 'closed'
            messages.success(request, f'Attendance session {status}.')
            return redirect('take_attendance', session_pk=session_pk)

        if action == 'save_marks':
            records = AttendanceRecord.objects.filter(session=session)
            for record in records:
                field_name = f'status_{record.student.pk}'
                new_status = request.POST.get(field_name, 'absent')
                record.status     = new_status
                record.marked_by  = 'teacher'
                record.save()
            messages.success(request, 'Attendance saved successfully!')
            return redirect('attendance_list', course_pk=session.course.pk)

    records = AttendanceRecord.objects.filter(
        session=session
    ).select_related('student').order_by('student__username')

    return render(request, 'attendance/take_attendance.html', {
        'session': session,
        'records': records,
    })


# ── STUDENT: Mark own attendance (when session is open) ───────
@login_required
def mark_self_attendance(request, session_pk):
    session = get_object_or_404(AttendanceSession, pk=session_pk, is_open=True)

    # Enforce IST 11:59 PM deadline
    from datetime import datetime, time, timedelta, timezone as dt_timezone
    ist_tz = dt_timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist_tz)
    session_date = session.date
    if now_ist.date() > session_date or (now_ist.date() == session_date and now_ist.time() > time(23, 59, 0)):
        session.is_open = False
        session.save()
        messages.error(request, 'The deadline (11:59 PM IST) to mark your own attendance for this session has passed.')
        return redirect('student_attendance', course_pk=session.course.pk)

    # Must be enrolled
    if not Enrollment.objects.filter(
        student=request.user, course=session.course, status='approved'
    ).exists():
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('course_list')

    record, created = AttendanceRecord.objects.get_or_create(
        session=session, student=request.user,
        defaults={'status': 'absent', 'marked_by': 'self'}
    )

    if request.method == 'POST':
        if record.status == 'present':
            messages.info(
                request, 'Your attendance is already marked as Present.'
            )
        else:
            record.status    = 'present'
            record.marked_by = 'self'
            record.save()
            messages.success(
                request,
                f'Attendance marked as Present for {session.course.title} on {session.date}!'
            )
        return redirect('student_attendance', course_pk=session.course.pk)

    return render(request, 'attendance/mark_self.html', {
        'session': session,
        'record':  record,
    })


# ── STUDENT: View own attendance summary for a course ─────────
@login_required
def student_attendance(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)

    # Check enrollment
    if not Enrollment.objects.filter(
        student=request.user, course=course, status='approved'
    ).exists() and course.teacher != request.user:
        messages.error(request, 'Access denied.')
        return redirect('course_list')

    # For teacher viewing a specific student
    student_id = request.GET.get('student')
    if student_id and course.teacher == request.user:
        student = get_object_or_404(CustomUser, pk=student_id)
    else:
        student = request.user

    sessions = AttendanceSession.objects.filter(course=course)
    total    = sessions.count()

    records  = AttendanceRecord.objects.filter(
        session__course=course, student=student
    ).select_related('session').order_by('session__date')

    present_count = records.filter(status='present').count()
    absent_count  = total - present_count
    percentage    = round((present_count / total * 100), 1) if total else 0

    # Open sessions student hasn't marked yet
    open_sessions = []
    if student == request.user and request.user.is_student():
        from datetime import datetime, time, timedelta, timezone as dt_timezone
        ist_tz = dt_timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist_tz)
        for session in sessions.filter(is_open=True):
            # Enforce IST 11:59 PM deadline
            session_date = session.date
            if now_ist.date() > session_date or (now_ist.date() == session_date and now_ist.time() > time(23, 59, 0)):
                session.is_open = False
                session.save()
                continue
            rec = records.filter(session=session).first()
            if not rec or (rec.status == 'absent' and rec.marked_by == 'teacher'):
                open_sessions.append(session)


    return render(request, 'attendance/student_attendance.html', {
        'course':         course,
        'student':        student,
        'records':        records,
        'total':          total,
        'present_count':  present_count,
        'absent_count':   absent_count,
        'percentage':     percentage,
        'open_sessions':  open_sessions,
        'is_own':         (student == request.user),
    })
