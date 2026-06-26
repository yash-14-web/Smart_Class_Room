from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse
import json

from courses.models import Course, Enrollment

from .forms import CodingTestCaseForm, QuestionCreateForm, TestCreateForm, TestTakeForm
from .models import CodingTestCase, Question, StudentResponse, Test
from .services import evaluate_coding_question


def _student_is_enrolled(user, course):
    return Enrollment.objects.filter(student=user, course=course, status='approved').exists()


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
            
            # Notify approved students
            from users.models import notify_user
            from courses.models import Enrollment
            enrolled = Enrollment.objects.filter(course=test.course, status='approved')
            for e in enrolled:
                notify_user(e.student, "New Test Scheduled", f"A new test '{test.title}' has been scheduled for course '{test.course.title}'.", "test")

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
            return redirect('question_add', test_id=test.pk)
    else:
        form = QuestionCreateForm()
    return render(request, 'tests/question_add.html', {
        'form': form,
        'test': test,
        'questions': test.questions.prefetch_related('test_cases').all()
    })


@login_required
def test_generate_ai(request, test_id):
    """API endpoint to generate test questions (MCQs & Coding) via AI."""
    test = get_object_or_404(Test, pk=test_id, created_by=request.user)
    if request.method == 'POST':
        topic = request.POST.get('topic')
        question_type = request.POST.get('question_type', 'mixed')
        num_questions = int(request.POST.get('num_questions', 3))
        difficulty = request.POST.get('difficulty', 'medium')
        marks_per_q = int(request.POST.get('marks', 5))

        from .ai_generator import generate_test_questions
        questions, error = generate_test_questions(topic, question_type, num_questions, difficulty)

        if error:
            return JsonResponse({'success': False, 'error': error})

        # Override marks with the teacher's choice
        for q in questions:
            q['marks'] = marks_per_q

        return JsonResponse({'success': True, 'questions': questions})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def test_save_bulk(request, test_id):
    """API endpoint to save bulk questions (MCQs & Coding with test cases) generated by AI."""
    test = get_object_or_404(Test, pk=test_id, created_by=request.user)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            questions_data = data.get('questions', [])
            for q_data in questions_data:
                q_type = q_data.get('question_type')
                # Clean up "none" placeholder values from JSON response before saving
                option1 = q_data.get('option1', '')
                if option1 == 'none': option1 = ''
                option2 = q_data.get('option2', '')
                if option2 == 'none': option2 = ''
                option3 = q_data.get('option3', '')
                if option3 == 'none': option3 = ''
                option4 = q_data.get('option4', '')
                if option4 == 'none': option4 = ''
                correct_answer = q_data.get('correct_answer', '')
                if correct_answer == 'none': correct_answer = ''

                expected_function_name = q_data.get('expected_function_name', '')
                if expected_function_name == 'none': expected_function_name = ''
                starter_code = q_data.get('starter_code', '')
                if starter_code == 'none': starter_code = ''
                reference_solution = q_data.get('reference_solution', '')
                if reference_solution == 'none': reference_solution = ''

                if q_type == Question.QUESTION_TYPE_MCQ:
                    Question.objects.create(
                        test=test,
                        question_type=Question.QUESTION_TYPE_MCQ,
                        question_text=q_data['question_text'],
                        marks=q_data.get('marks', 1),
                        option1=option1,
                        option2=option2,
                        option3=option3,
                        option4=option4,
                        correct_answer=correct_answer
                    )
                elif q_type == Question.QUESTION_TYPE_CODING:
                    question = Question.objects.create(
                        test=test,
                        question_type=Question.QUESTION_TYPE_CODING,
                        question_text=q_data['question_text'],
                        marks=q_data.get('marks', 5),
                        expected_function_name=expected_function_name,
                        starter_code=starter_code,
                        reference_solution=reference_solution
                    )
                    
                    # Create test cases
                    test_cases = q_data.get('test_cases', [])
                    for idx, case_data in enumerate(test_cases):
                        # Ensure input_data is a string representation of arguments, default to '[]' if empty
                        inp = case_data.get('input_data', '[]')
                        out = case_data.get('expected_output', '')
                        CodingTestCase.objects.create(
                            question=question,
                            order=idx + 1,
                            input_data=inp,
                            expected_output=out,
                            is_sample=case_data.get('is_sample', False),
                            weight=case_data.get('weight', 1),
                            explanation=case_data.get('explanation', '')
                        )

            test.refresh_total_marks()
            return JsonResponse({'success': True, 'message': f'{len(questions_data)} questions added.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def question_delete_view(request, question_id):
    """View to delete a specific question from a test."""
    question = get_object_or_404(Question, pk=question_id)
    test = question.test
    if not request.user.is_teacher() or test.created_by != request.user:
        messages.error(request, 'Only the teacher who created the test can delete questions.')
        return redirect('test_list')

    question.delete()
    messages.success(request, 'Question deleted successfully.')
    return redirect('question_add', test_id=test.pk)


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
    if existing and not existing.retake_allowed:
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
        action = request.POST.get('action', 'submit')
        if action == 'run':
            form = TestTakeForm(request.POST, questions=questions)
            for question in questions:
                if question.is_mcq():
                    field_name = f'question_{question.pk}'
                    if field_name in form.fields:
                        form.fields[field_name].required = False
            if form.is_valid():
                results_payload = {}
                target_qid = request.POST.get('question_id')
                coding_questions = [q for q in questions if q.is_coding()]
                for question in coding_questions:
                    if target_qid and str(question.pk) != str(target_qid):
                        continue
                    code = form.cleaned_data.get(f'code_{question.pk}', '')
                    result = evaluate_coding_question(
                        question,
                        code,
                        run_all=True,
                    )
                    # Redact hidden test cases details
                    if 'results' in result:
                        for r in result['results']:
                            if not r['is_sample']:
                                r['input_preview'] = '[Hidden]'
                                r['expected_preview'] = '[Hidden]'
                                r['actual_preview'] = '[Hidden]'
                                r['explanation'] = 'Hidden grading test case.'
                    results_payload[str(question.pk)] = result
                return JsonResponse({'success': True, 'feedback': results_payload})
            else:
                return JsonResponse({'success': False, 'error': 'Form invalid: ' + str(form.errors)})
        
        form = TestTakeForm(request.POST, questions=questions)
        if form.is_valid():
            if False:  # dead branch left for safety
                pass
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
                if existing:
                    existing.score = total_score
                    existing.quiz_score = round(quiz_score, 2)
                    existing.coding_score = round(coding_score, 2)
                    existing.answers_payload = answers_payload
                    existing.coding_submissions = coding_submissions
                    existing.evaluation_summary = evaluation_summary
                    existing.submitted_at = timezone.now()
                    existing.retake_allowed = False
                    existing.retake_requested = False
                    existing.save()
                else:
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
    missed_students = Enrollment.objects.filter(course=test.course, status='approved').exclude(
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


@login_required
def test_answer_key_view(request, test_id):
    """View to show the official answer key of a test (accessible only to teachers)."""
    test = get_object_or_404(Test, pk=test_id)
    if not request.user.is_teacher() or test.created_by != request.user:
        messages.error(request, 'Only the teacher who created the test can view the answer key.')
        return redirect('test_list')

    questions = test.questions.prefetch_related('test_cases').all()
    return render(request, 'tests/test_answer_key.html', {
        'test': test,
        'questions': questions,
    })


@login_required
def test_request_retake_view(request, test_id):
    """View for students to request an exam retake from the teacher."""
    test = get_object_or_404(Test, pk=test_id)
    response = get_object_or_404(StudentResponse, student=request.user, test=test)
    
    if response.retake_allowed:
        messages.info(request, 'You already have permission to take this exam again.')
    else:
        response.retake_requested = True
        response.save()
        messages.success(request, 'Your request for a retake has been sent to the teacher.')
        
    return redirect('test_detail', test_id=test.pk)


@login_required
def test_grant_retake_view(request, test_id, response_id):
    """View for teachers to grant an exam retake access to a student."""
    test = get_object_or_404(Test, pk=test_id)
    if not request.user.is_teacher() or test.created_by != request.user:
        messages.error(request, 'Only the creator of this test can grant retakes.')
        return redirect('test_list')
        
    response = get_object_or_404(StudentResponse, pk=response_id, test=test)
    response.retake_allowed = True
    response.retake_requested = False
    response.save()

    # Notify student
    from users.models import notify_user
    notify_user(response.student, "Retake Permission Granted", f"Your request to retake the test '{test.title}' has been granted. You can take the test again now.", "test")
    
    messages.success(request, f'Retake permission granted to student {response.student.username}.')
    return redirect('test_responses', test_id=test.pk)


@login_required
def test_reject_retake_view(request, test_id, response_id):
    """View for teachers to reject an exam retake request."""
    test = get_object_or_404(Test, pk=test_id)
    if not request.user.is_teacher() or test.created_by != request.user:
        messages.error(request, 'Only the creator of this test can reject retakes.')
        return redirect('test_list')
        
    response = get_object_or_404(StudentResponse, pk=response_id, test=test)
    response.retake_allowed = False
    response.retake_requested = False
    response.save()

    # Notify student
    from users.models import notify_user
    notify_user(response.student, "Retake Request Rejected", f"Your request to retake the test '{test.title}' has been rejected.", "test")
    
    messages.warning(request, f'Retake request rejected for student {response.student.username}.')
    return redirect('test_responses', test_id=test.pk)

