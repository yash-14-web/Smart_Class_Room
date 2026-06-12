from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from courses.models import Course, Enrollment

from .forms import CodingTestCaseForm, QuestionCreateForm, TestCreateForm, TestTakeForm
from .models import CodingTestCase, Question, StudentResponse, Test
from .services import evaluate_coding_question


def _student_is_enrolled(user, course):
    return Enrollment.objects.filter(student=user, course=course).exists()


@login_required
def test_list_view(request, course_pk=None):
    course = None
    from django.db.models import Q
    if course_pk is not None:
        course = get_object_or_404(Course, pk=course_pk)
        if request.user.is_teacher():
            tests = Test.objects.filter(course=course, created_by=request.user).order_by('-created_at')
        else:
            if not _student_is_enrolled(request.user, course):
                messages.error(request, 'You must be enrolled in the course to view its tests.')
                return redirect('course_list')
            tests = Test.objects.filter(
                Q(course=course, is_active=True) &
                (Q(assigned_to=request.user) | Q(assigned_to__isnull=True))
            ).distinct().order_by('-created_at')
    else:
        if request.user.is_teacher():
            tests = Test.objects.filter(created_by=request.user).order_by('-created_at')
        else:
            tests = Test.objects.filter(
                Q(is_active=True, course__enrollments__student=request.user) &
                (Q(assigned_to=request.user) | Q(assigned_to__isnull=True))
            ).distinct().order_by('-created_at')
    return render(request, 'tests/test_list.html', {'tests': tests, 'course': course})


@login_required
def test_create_view(request, course_pk=None):
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can create tests.')
        return redirect('test_list')

    course = None
    initial = {}
    if course_pk:
        course = get_object_or_404(Course, pk=course_pk, teacher=request.user)
        initial['course'] = course

    if request.method == 'POST':
        form = TestCreateForm(request.POST, request.FILES, user=request.user, course=course)
        if form.is_valid():
            test = form.save(commit=False)
            test.created_by = request.user
            test.save()
            form.save_m2m()
            messages.success(request, 'Test created. Add quiz or coding questions next.')
            return redirect('test_detail', test_id=test.pk)
    else:
        form = TestCreateForm(user=request.user, initial=initial, course=course)
    return render(request, 'tests/test_create.html', {'form': form, 'course': course})


@login_required
def test_detail_view(request, test_id):
    test = get_object_or_404(Test.objects.select_related('course', 'created_by'), pk=test_id)
    if request.user.is_teacher() and test.created_by != request.user:
        messages.error(request, 'You can only view your own tests.')
        return redirect('test_list')

    if request.user.is_student() and not _student_is_enrolled(request.user, test.course):
        messages.error(request, 'You must be enrolled in this course to view the test.')
        return redirect('course_list')

    if request.user.is_student():
        if test.assigned_to.exists() and not test.assigned_to.filter(id=request.user.id).exists():
            messages.error(request, 'You are not assigned to this test.')
            return redirect('course_detail', pk=test.course.pk)
            
        now = timezone.now()
        if test.available_from and now < test.available_from:
            messages.error(request, 'This test is not open yet. It will be available starting at {}.'.format(
                timezone.localtime(test.available_from).strftime('%b %d, %Y %H:%M')
            ))
            if test.course:
                return redirect('test_course_list', course_pk=test.course.pk)
            return redirect('test_list')

    questions = test.questions.prefetch_related('test_cases').all()
    response = None
    if not request.user.is_teacher():
        response = StudentResponse.objects.filter(student=request.user, test=test).first()

    return render(request, 'tests/test_detail.html', {
        'test': test,
        'questions': questions,
        'response': response,
        'response_summary': response.evaluation_summary if response else [],
    })


@login_required
def test_edit_view(request, test_id):
    test = get_object_or_404(Test, pk=test_id)
    if not request.user.is_teacher() or test.created_by != request.user:
        messages.error(request, 'Only the teacher who created the test can edit it.')
        return redirect('test_list')

    if request.method == 'POST':
        form = TestCreateForm(request.POST, request.FILES, instance=test, user=request.user, course=test.course)
        if form.is_valid():
            test = form.save(commit=False)
            test.save()
            form.save_m2m()
            messages.success(request, 'Test updated successfully.')
            return redirect('test_detail', test_id=test.pk)
    else:
        form = TestCreateForm(instance=test, user=request.user, course=test.course)
    return render(request, 'tests/test_edit.html', {'form': form, 'test': test})

@login_required
def test_delete_view(request, test_id):
    test = get_object_or_404(Test, pk=test_id)
    if not request.user.is_teacher() or test.created_by != request.user:
        messages.error(request, 'Only the creator can delete this test.')
        return redirect('test_list')

    if request.method == 'POST':
        test.delete()
        messages.success(request, 'Test deleted successfully.')
        return redirect('test_list')
    return render(request, 'tests/test_delete.html', {'test': test})


@login_required
def question_add_view(request, test_id):
    test = get_object_or_404(Test, pk=test_id)
    if not request.user.is_teacher() or test.created_by != request.user:
        messages.error(request, 'Only the teacher who created the test can add questions.')
        return redirect('test_list')

    if request.method == 'POST':
        form = QuestionCreateForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.test = test
            question.save()
            if question.question_type == Question.QUESTION_TYPE_CODING:
                messages.success(request, 'Coding question added. Now create sample and hidden grading cases.')
                return redirect('coding_testcase_add', question_id=question.pk)
            messages.success(request, 'Quiz question added to the test.')
            return redirect('test_detail', test_id=test.pk)
    else:
        form = QuestionCreateForm()
    return render(request, 'tests/question_add.html', {'form': form, 'test': test})


@login_required
def coding_testcase_add_view(request, question_id):
    question = get_object_or_404(Question.objects.select_related('test'), pk=question_id)
    if not request.user.is_teacher() or question.test.created_by != request.user:
        messages.error(request, 'Only the teacher who created the test can add coding test cases.')
        return redirect('test_list')

    if question.question_type != Question.QUESTION_TYPE_CODING:
        messages.error(request, 'Coding test cases can only be added to coding questions.')
        return redirect('test_detail', test_id=question.test.pk)

    if request.method == 'POST':
        form = CodingTestCaseForm(request.POST)
        if form.is_valid():
            test_case = form.save(commit=False)
            test_case.question = question
            test_case.save()
            messages.success(request, 'Test case added.')
            return redirect('coding_testcase_add', question_id=question.pk)
    else:
        form = CodingTestCaseForm(initial={'order': question.test_cases.count() + 1})

    return render(request, 'tests/coding_testcase_form.html', {
        'form': form,
        'question': question,
        'test': question.test,
        'existing_cases': question.test_cases.all(),
    })


@login_required
def test_take_view(request, test_id):
    test = get_object_or_404(Test, pk=test_id)
    if request.user.is_teacher():
        messages.error(request, 'Teachers cannot take tests.')
        return redirect('test_detail', test_id=test.pk)

    if not _student_is_enrolled(request.user, test.course):
        messages.error(request, 'You must be enrolled in this course to take the test.')
        return redirect('course_list')

    # Access control: only assigned students can take
    if test.assigned_to.exists() and not test.assigned_to.filter(id=request.user.id).exists():
        messages.error(request, 'You are not assigned to this test.')
        return redirect('course_detail', pk=test.course.pk)

    existing = StudentResponse.objects.filter(student=request.user, test=test).first()
    if existing:
        messages.info(request, 'You have already submitted this test.')
        return redirect('test_detail', test_id=test.pk)

    questions = list(test.questions.prefetch_related('test_cases').all())
    if not questions:
        messages.warning(request, 'This test does not yet have questions.')
        return redirect('test_detail', test_id=test.pk)

    now = timezone.now()
    if not test.is_open():
        if test.available_from and now < test.available_from:
            messages.error(request, 'This test is not open yet. It will be available starting at {}.'.format(
                timezone.localtime(test.available_from).strftime('%b %d, %Y %H:%M')
            ))
        else:
            messages.error(request, 'This test is not currently available.')
        if test.course:
            return redirect('test_course_list', course_pk=test.course.pk)
        return redirect('test_list')

    session_key = f'test_start_{test.pk}'
    started_at_text = request.session.get(session_key)
    if started_at_text:
        started_at = timezone.datetime.fromisoformat(started_at_text)
        if started_at.tzinfo is None:
            started_at = timezone.make_aware(started_at, timezone.get_current_timezone())
    else:
        started_at = now
        request.session[session_key] = started_at.isoformat()

    elapsed = now - started_at
    remaining_seconds = max(0, test.time_limit * 60 - int(elapsed.total_seconds()))
    remaining_minutes = remaining_seconds // 60
    if remaining_seconds <= 0:
        request.session.pop(session_key, None)
        messages.error(request, 'Time limit exceeded. The test can no longer be submitted.')
        return redirect('test_detail', test_id=test.pk)

    sample_feedback = {}
    if request.method == 'POST':
        form = TestTakeForm(request.POST, questions=questions)
        action = request.POST.get('action', 'submit')
        if action == 'run':
            for question in questions:
                if question.is_mcq():
                    form.fields[f'question_{question.pk}'].required = False
        if form.is_valid():
            if action == 'run':
                coding_questions = [question for question in questions if question.is_coding()]
                for question in coding_questions:
                    code = form.cleaned_data.get(f'code_{question.pk}', '')
                    sample_feedback[str(question.pk)] = evaluate_coding_question(
                        question,
                        code,
                        include_hidden=False,
                    )
                messages.info(request, 'Sample tests finished. Final hidden grading will happen on submit.')
            else:
                quiz_score = 0.0
                coding_score = 0.0
                answers_payload = {}
                coding_submissions = {}
                evaluation_summary = []

                for question in questions:
                    if question.is_mcq():
                        answer = form.cleaned_data.get(f'question_{question.pk}')
                        answers_payload[str(question.pk)] = answer
                        obtained = float(question.marks if answer == question.correct_answer else 0)
                        quiz_score += obtained
                        evaluation_summary.append({
                            'question_id': question.pk,
                            'title': question.question_text,
                            'type': 'Quiz',
                            'obtained_marks': obtained,
                            'total_marks': question.marks,
                            'status': 'Pass' if obtained else 'Fail',
                        })
                    else:
                        code = form.cleaned_data.get(f'code_{question.pk}', '')
                        coding_submissions[str(question.pk)] = code
                        result = evaluate_coding_question(question, code, include_hidden=True)
                        coding_score += result['obtained_marks']
                        evaluation_summary.append({
                            'question_id': question.pk,
                            'title': question.question_text,
                            'type': 'Coding',
                            'obtained_marks': result['obtained_marks'],
                            'total_marks': result['total_marks'],
                            'status': 'Pass' if result['obtained_marks'] >= (question.marks * 0.4) else 'Fail',
                            'passed_cases': result['passed_cases'],
                            'total_cases': result['total_cases'],
                            'error': result['error'],
                            'stdout': result['stdout'],
                        })

                total_score = round(quiz_score + coding_score, 2)
                StudentResponse.objects.create(
                    student=request.user,
                    test=test,
                    score=total_score,
                    quiz_score=round(quiz_score, 2),
                    coding_score=round(coding_score, 2),
                    answers_payload=answers_payload,
                    coding_submissions=coding_submissions,
                    evaluation_summary=evaluation_summary,
                    submitted_at=timezone.now(),
                )
                request.session.pop(session_key, None)
                messages.success(request, f'Your test was submitted successfully. Total score: {total_score}.')
                return redirect('test_detail', test_id=test.pk)
    else:
        form = TestTakeForm(questions=questions)

    form_rows = []
    for question in questions:
        field_name = f'question_{question.pk}' if question.is_mcq() else f'code_{question.pk}'
        form_rows.append({
            'question': question,
            'field': form[field_name],
            'feedback': sample_feedback.get(str(question.pk)),
        })

    return render(request, 'tests/test_take.html', {
        'test': test,
        'form': form,
        'questions': questions,
        'form_rows': form_rows,
        'remaining_seconds': remaining_seconds,
        'remaining_minutes': remaining_minutes,
        'started_at': started_at,
        'sample_feedback': sample_feedback,
    })


@login_required
def test_responses_view(request, test_id):
    test = get_object_or_404(Test, pk=test_id)
    if not request.user.is_teacher() or test.created_by != request.user:
        messages.error(request, 'Only the creator can view responses.')
        return redirect('test_list')

    responses = test.responses.select_related('student').order_by('-submitted_at')
    submitted_student_ids = responses.values_list('student_id', flat=True)
    missed_students = Enrollment.objects.filter(course=test.course).exclude(
        student_id__in=submitted_student_ids
    ).select_related('student')
    return render(request, 'tests/test_responses.html', {
        'test': test,
        'responses': responses,
        'missed_students': missed_students,
    })


@login_required
def test_response_detail_view(request, test_id, response_id):
    test = get_object_or_404(Test, pk=test_id)
    response = get_object_or_404(
        StudentResponse.objects.select_related('student', 'test'),
        pk=response_id,
        test=test,
    )
    if request.user.is_teacher():
        if test.created_by != request.user:
            messages.error(request, 'Only the creator can review this submission.')
            return redirect('test_list')
    elif response.student != request.user:
        messages.error(request, 'You are not allowed to view this response.')
        return redirect('test_list')

    questions_by_id = {str(question.pk): question for question in test.questions.all()}
    coding_entries = []
    for question_id, code in response.coding_submissions.items():
        question = questions_by_id.get(str(question_id))
        if question:
            coding_entries.append({
                'question': question,
                'code': code,
            })

    return render(request, 'tests/test_response_detail.html', {
        'test': test,
        'response': response,
        'summary_rows': response.evaluation_summary,
        'coding_entries': coding_entries,
    })

