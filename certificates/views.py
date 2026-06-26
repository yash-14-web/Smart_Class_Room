from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Certificate
from courses.models import Course, Enrollment
from users.models import CustomUser
from assignments.models import Submission
from django.db.models import Sum, Avg
import io
import math


def _get_accessible_certificate(request, cert_pk):
    certificate = get_object_or_404(Certificate, pk=cert_pk)
    if (certificate.student != request.user and
            certificate.course.teacher != request.user):
        messages.error(request, 'Access denied.')
        return None
    return certificate


def _get_student_performance(student, course):
    """Returns performance summary for a student in a course."""
    subs = Submission.objects.filter(
        student=student,
        assignment__course=course,
        grade__isnull=False
    )
    total_marks   = sum(s.assignment.total_marks for s in subs)
    total_scored  = subs.aggregate(t=Sum('grade'))['t'] or 0
    avg_pct       = round((total_scored / total_marks * 100), 1) if total_marks else 0
    pending_count = Submission.objects.filter(
        student=student,
        assignment__course=course,
        grade__isnull=True
    ).count()
    not_submitted = course.assignments.count() - subs.count() - pending_count

    # Quiz scores
    from quiz.models import QuizAttempt
    quiz_attempts = QuizAttempt.objects.filter(
        student=student, quiz__course=course, is_complete=True
    )
    quiz_total  = sum(a.quiz.total_marks for a in quiz_attempts)
    quiz_scored = sum(a.score for a in quiz_attempts)

    # Combined
    combined_total  = total_marks + quiz_total
    combined_scored = total_scored + quiz_scored
    combined_avg    = round((combined_scored / combined_total * 100), 1) if combined_total else 0

    overall_pass = 'Pass' if combined_avg >= 40 else ('Pending' if combined_total == 0 else 'Fail')

    return {
        'total_marks':    combined_total,
        'total_scored':   combined_scored,
        'avg_pct':        combined_avg,
        'pending_count':  pending_count,
        'not_submitted':  not_submitted,
        'overall_pass':   overall_pass,
    }


@login_required
def issue_certificate(request, course_pk):
    course      = get_object_or_404(Course, pk=course_pk, teacher=request.user)
    enrollments = Enrollment.objects.filter(course=course, status='approved').select_related('student')

    if request.method == 'POST':
        student_id  = request.POST.get('student_id')
        badge_type  = request.POST.get('badge_type', 'completion')
        title       = request.POST.get('title', '')
        description = request.POST.get('description', '')
        student     = get_object_or_404(CustomUser, pk=student_id)

        cert, created = Certificate.objects.get_or_create(
            student=student, course=course, badge_type=badge_type,
            defaults={
                'issued_by':   request.user,
                'title':       title,
                'description': description,
            }
        )
        if created:
            messages.success(request, f'Certificate issued to {student.username}!')
        else:
            messages.info(request, f'{student.username} already has this certificate.')
        return redirect('issue_certificate', course_pk=course_pk)

    # Build performance data for each student so teacher can see before issuing
    student_performance = []
    for enrollment in enrollments:
        perf = _get_student_performance(enrollment.student, course)
        existing_cert = Certificate.objects.filter(
            student=enrollment.student, course=course
        ).first()
        student_performance.append({
            'student':       enrollment.student,
            'enrolled_at':   enrollment.enrolled_at,
            'performance':   perf,
            'has_cert':      existing_cert is not None,
            'cert':          existing_cert,
        })

    # Sort: Pass first, then Pending, then Fail
    order = {'Pass': 0, 'Pending': 1, 'Fail': 2}
    student_performance.sort(
        key=lambda x: order.get(x['performance']['overall_pass'], 3)
    )

    certificates = Certificate.objects.filter(
        course=course
    ).select_related('student')

    return render(request, 'certificates/issue_certificate.html', {
        'course':               course,
        'student_performance':  student_performance,
        'certificates':         certificates,
    })


@login_required
def my_certificates(request):
    certificates = Certificate.objects.filter(
        student=request.user
    ).select_related('course', 'issued_by').order_by('-issued_at')
    return render(request, 'certificates/my_certificates.html', {
        'certificates': certificates,
    })


@login_required
def view_certificate(request, cert_pk):
    certificate = _get_accessible_certificate(request, cert_pk)
    if certificate is None:
        return redirect('dashboard')
    return render(request, 'certificates/certificate_view.html', {
        'certificate': certificate,
    })


@login_required
def certificate_exact_view(request, cert_pk):
    certificate = _get_accessible_certificate(request, cert_pk)
    if certificate is None:
        return redirect('dashboard')

    context = _build_cert_context(certificate)
    return render(request, 'certificates/certificate_exact.html', context)


def _build_cert_context(certificate):
    from django.utils import timezone
    valid_date = certificate.issued_at.replace(
        year=certificate.issued_at.year + 2
    )
    return {
        'student_name':    certificate.student.get_full_name() or certificate.student.username,
        'course_name':     certificate.course.title,
        'issue_date':      certificate.issued_at.strftime('%d/%m/%Y'),
        'valid_date':      valid_date.strftime('%d/%m/%Y'),
        'points':          '8',
        'duration':        '40-hour',
        'company_name':    'SmartClass',
        'instructor_name': certificate.issued_by.get_full_name() or certificate.issued_by.username,
        'instructor_role': 'Course Teacher',
        'company_address': 'Chennai, India',
        'email':           certificate.issued_by.email or 'smartclass@example.com',
        'phone':           '9876543210',
        'cert_id':         f'SCM-{certificate.pk:06d}',
        'certificate':     certificate,
    }


from django.conf import settings
import base64

@login_required
def download_certificate_pdf(request, cert_pk):
    certificate = _get_accessible_certificate(request, cert_pk)
    if certificate is None:
        return redirect('dashboard')

    logo_base64 = ""
    try:
        logo_path = settings.MEDIA_ROOT / 'smart_logo.png'
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception:
        pass

    return render(
        request,
        'certificates/certificate_print.html',
        {
            'certificate': certificate,
            'auto_print': True,
            'logo_base64': logo_base64
        }
    )


@login_required
def download_certificate_exact_pdf(request, cert_pk):
    certificate = _get_accessible_certificate(request, cert_pk)
    if certificate is None:
        return redirect('dashboard')

    logo_base64 = ""
    try:
        logo_path = settings.MEDIA_ROOT / 'smart_logo.png'
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception:
        pass

    return render(
        request,
        'certificates/certificate_print.html',
        {
            'certificate': certificate,
            'auto_print': True,
            'logo_base64': logo_base64
        }
    )
