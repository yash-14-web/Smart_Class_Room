from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import ProjectSubmissionForm, ProjectGradeForm
from .models import ProjectSubmission


@login_required
def project_list_view(request):
    if request.user.is_teacher():
        submissions = ProjectSubmission.objects.order_by('-submitted_at')
    else:
        submissions = ProjectSubmission.objects.filter(student=request.user).order_by('-submitted_at')
    return render(request, 'projects/project_list.html', {'submissions': submissions})


@login_required
def project_submit_view(request):
    if request.user.is_teacher():
        messages.error(request, 'Only students can submit projects.')
        return redirect('project_list')

    if request.method == 'POST':
        form = ProjectSubmissionForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.student = request.user
            submission.save()
            messages.success(request, 'Project submitted successfully.')
            return redirect('project_list')
    else:
        form = ProjectSubmissionForm(user=request.user)
    return render(request, 'projects/project_form.html', {'form': form})


@login_required
def project_detail_view(request, pk):
    submission = get_object_or_404(ProjectSubmission, pk=pk)
    if request.user != submission.student and not request.user.is_teacher():
        messages.error(request, 'You are not authorized to view this project.')
        return redirect('project_list')

    grade_form = None
    if request.user.is_teacher():
        if request.method == 'POST':
            grade_form = ProjectGradeForm(request.POST, instance=submission)
            if grade_form.is_valid():
                graded_submission = grade_form.save(commit=False)
                graded_submission.graded_by = request.user
                graded_submission.graded_at = timezone.now()
                graded_submission.save()
                messages.success(request, 'Project score updated successfully.')
                return redirect('project_detail', pk=submission.pk)
        else:
            grade_form = ProjectGradeForm(instance=submission)

    return render(request, 'projects/project_detail.html', {
        'submission': submission,
        'grade_form': grade_form,
    })


@login_required
def project_delete_view(request, pk):
    submission = get_object_or_404(ProjectSubmission, pk=pk)
    if request.user != submission.student:
        messages.error(request, 'You are not authorized to delete this submission.')
        return redirect('project_list')

    if request.method == 'POST':
        submission.delete()
        messages.success(request, 'Project submission deleted successfully.')
        return redirect('project_list')

    return render(request, 'projects/project_confirm_delete.html', {'submission': submission})
