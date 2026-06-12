from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Quiz, Question, Choice, QuizAttempt, StudentAnswer
from courses.models import Course, Enrollment


@login_required
def quiz_list(request, course_pk):
    course       = get_object_or_404(Course, pk=course_pk)
    if request.user.is_teacher():
        quizzes = Quiz.objects.filter(course=course)
    else:
        from django.db.models import Q
        quizzes = Quiz.objects.filter(
            Q(course=course, is_active=True) &
            (Q(assigned_to=request.user) | Q(assigned_to__isnull=True))
        ).distinct()

    attempted_ids = []
    if request.user.is_student():
        attempted_ids = list(QuizAttempt.objects.filter(
            student=request.user, quiz__course=course, is_complete=True
        ).values_list('quiz_id', flat=True))

    # For teacher: get attempt counts per quiz
    attempt_counts = {}
    if request.user.is_teacher():
        for quiz in quizzes:
            attempt_counts[quiz.pk] = QuizAttempt.objects.filter(
                quiz=quiz, is_complete=True
            ).count()

    now = timezone.now()
    return render(request, 'quiz/quiz_list.html', {
        'course':         course,
        'quizzes':        quizzes,
        'attempted_ids':  attempted_ids,
        'attempt_counts': attempt_counts,
        'now':            now,
    })


@login_required
def quiz_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, teacher=request.user)
    if request.method == 'POST':
        title       = request.POST.get('title')
        description = request.POST.get('description', '')
        duration    = request.POST.get('duration', 30)
        start_date  = request.POST.get('start_date') or None
        due_date    = request.POST.get('due_date') or None
        assigned_to_ids = request.POST.getlist('assigned_to')
        
        quiz = Quiz.objects.create(
            course=course,
            title=title,
            description=description,
            duration=int(duration),
            start_date=start_date,
            due_date=due_date
        )
        if assigned_to_ids:
            quiz.assigned_to.set(assigned_to_ids)
            
        messages.success(request, f'Quiz "{quiz.title}" created! Now add questions.')
        return redirect('quiz_add_questions', quiz_pk=quiz.pk)
        
    enrolled_students = Enrollment.objects.filter(course=course).select_related('student')
    return render(request, 'quiz/quiz_create.html', {
        'course': course,
        'enrolled_students': enrolled_students,
    })


@login_required
def quiz_edit(request, quiz_pk):
    quiz = get_object_or_404(Quiz, pk=quiz_pk, course__teacher=request.user)
    if request.method == 'POST':
        quiz.title       = request.POST.get('title')
        quiz.description = request.POST.get('description', '')
        quiz.duration    = int(request.POST.get('duration', quiz.duration))
        quiz.start_date  = request.POST.get('start_date') or None
        quiz.due_date    = request.POST.get('due_date') or None
        quiz.is_active   = bool(request.POST.get('is_active'))
        quiz.save()
        
        assigned_to_ids = request.POST.getlist('assigned_to')
        quiz.assigned_to.set(assigned_to_ids)
        
        messages.success(request, f'Quiz "{quiz.title}" updated.')
        return redirect('quiz_add_questions', quiz_pk=quiz.pk)
        
    enrolled_students = Enrollment.objects.filter(course=quiz.course).select_related('student')
    assigned_ids = list(quiz.assigned_to.values_list('id', flat=True))
    return render(request, 'quiz/quiz_edit.html', {
        'quiz': quiz,
        'enrolled_students': enrolled_students,
        'assigned_ids': assigned_ids,
    })


@login_required
def quiz_add_questions(request, quiz_pk):
    quiz = get_object_or_404(Quiz, pk=quiz_pk, course__teacher=request.user)
    if request.method == 'POST':
        q_text   = request.POST.get('question_text')
        q_marks  = int(request.POST.get('marks', 1))
        choices  = request.POST.getlist('choice_text')
        correct  = request.POST.get('correct_choice')
        if q_text and choices:
            order    = quiz.questions.count() + 1
            question = Question.objects.create(
                quiz=quiz, text=q_text,
                marks=q_marks, order=order
            )
            for i, choice_text in enumerate(choices):
                if choice_text.strip():
                    Choice.objects.create(
                        question=question,
                        text=choice_text.strip(),
                        is_correct=(str(i) == correct)
                    )
            quiz.calculate_total()
            messages.success(request, 'Question added!')
        return redirect('quiz_add_questions', quiz_pk=quiz.pk)

    questions = quiz.questions.prefetch_related('choices').all()
    return render(request, 'quiz/quiz_add_questions.html', {
        'quiz':      quiz,
        'questions': questions,
    })


@login_required
def quiz_attempt(request, quiz_pk):
    quiz = get_object_or_404(Quiz, pk=quiz_pk, is_active=True)

    if not request.user.is_student():
        messages.error(request, 'Only students can attempt quizzes.')
        return redirect('quiz_list', course_pk=quiz.course.pk)

    if not Enrollment.objects.filter(
        student=request.user, course=quiz.course
    ).exists():
        messages.error(request, 'You must be enrolled to attempt this quiz.')
        return redirect('course_list')

    # Access control: only assigned students can attempt
    if quiz.assigned_to.exists() and not quiz.assigned_to.filter(id=request.user.id).exists():
        messages.error(request, 'You are not assigned to this quiz.')
        return redirect('quiz_list', course_pk=quiz.course.pk)

    existing = QuizAttempt.objects.filter(
        quiz=quiz, student=request.user
    ).first()
    if existing and existing.is_complete:
        messages.info(request, 'You have already completed this quiz.')
        return redirect('quiz_result', attempt_pk=existing.pk)

    now = timezone.now()
    if quiz.start_date and now < quiz.start_date:
        messages.error(request, 'Quiz is not available yet.')
        return redirect('quiz_list', course_pk=quiz.course.pk)
    if quiz.due_date and now > quiz.due_date:
        messages.error(request, 'Quiz deadline has passed.')
        return redirect('quiz_list', course_pk=quiz.course.pk)

    attempt, created = QuizAttempt.objects.get_or_create(
        quiz=quiz, student=request.user
    )

    if request.method == 'POST':
        score     = 0
        questions = quiz.questions.prefetch_related('choices').all()
        for question in questions:
            choice_id = request.POST.get(f'question_{question.pk}')
            if choice_id:
                try:
                    choice = Choice.objects.get(pk=choice_id, question=question)
                    StudentAnswer.objects.update_or_create(
                        attempt=attempt, question=question,
                        defaults={'choice': choice}
                    )
                    if choice.is_correct:
                        score += question.marks
                except Choice.DoesNotExist:
                    pass

        attempt.score       = score
        attempt.finished_at = timezone.now()
        attempt.is_complete = True
        attempt.save()
        messages.success(
            request, f'Quiz submitted! You scored {score}/{quiz.total_marks}.'
        )
        return redirect('quiz_result', attempt_pk=attempt.pk)

    questions = quiz.questions.prefetch_related('choices').all()
    return render(request, 'quiz/quiz_attempt.html', {
        'quiz':      quiz,
        'questions': questions,
        'attempt':   attempt,
    })


@login_required
def quiz_result(request, attempt_pk):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_pk)
    if (attempt.student != request.user and
            attempt.quiz.course.teacher != request.user):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    answers = attempt.answers.select_related('question', 'choice').all()
    return render(request, 'quiz/quiz_result.html', {
        'attempt': attempt,
        'answers': answers,
    })


@login_required
def quiz_submissions(request, quiz_pk):
    quiz     = get_object_or_404(Quiz, pk=quiz_pk, course__teacher=request.user)
    attempts = QuizAttempt.objects.filter(
        quiz=quiz, is_complete=True
    ).select_related('student').order_by('-score')
    return render(request, 'quiz/quiz_submissions.html', {
        'quiz':     quiz,
        'attempts': attempts,
    })


@login_required
def delete_question(request, question_pk):
    question = get_object_or_404(
        Question, pk=question_pk, quiz__course__teacher=request.user
    )
    quiz_pk = question.quiz.pk
    question.delete()
    question.quiz.calculate_total()
    messages.success(request, 'Question deleted.')
    return redirect('quiz_add_questions', quiz_pk=quiz_pk)


# ── FIX 4: Delete entire quiz ────────────────────────────────────
@login_required
def quiz_delete(request, quiz_pk):
    quiz      = get_object_or_404(Quiz, pk=quiz_pk, course__teacher=request.user)
    course_pk = quiz.course.pk
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, f'Quiz "{quiz.title}" deleted.')
        return redirect('quiz_list', course_pk=course_pk)
    return render(request, 'quiz/quiz_confirm_delete.html', {'quiz': quiz})


# ── FIX 4: Students who attempted a quiz ────────────────────────
@login_required
def quiz_attempted_students(request, quiz_pk):
    quiz     = get_object_or_404(Quiz, pk=quiz_pk, course__teacher=request.user)
    attempts = QuizAttempt.objects.filter(
        quiz=quiz, is_complete=True
    ).select_related('student').order_by('-score')

    # Students who have NOT attempted
    enrolled_ids = Enrollment.objects.filter(
        course=quiz.course
    ).values_list('student_id', flat=True)
    attempted_ids = attempts.values_list('student_id', flat=True)
    not_attempted = [
        eid for eid in enrolled_ids if eid not in attempted_ids
    ]

    from users.models import CustomUser
    not_attempted_students = CustomUser.objects.filter(id__in=not_attempted)

    return render(request, 'quiz/quiz_attempted_students.html', {
        'quiz':                  quiz,
        'attempts':              attempts,
        'not_attempted_students': not_attempted_students,
    })
