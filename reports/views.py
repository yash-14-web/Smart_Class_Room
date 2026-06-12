from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ReportCard
from .forms import ReportCardUpdateForm


@login_required
def report_card_view(request):
    if request.user.is_teacher():
        return redirect('report_list')
    return redirect('/users/report-card/')


@login_required
def report_list_view(request):
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can view report cards management.')
        return redirect('/users/report-card/')

    report_cards = ReportCard.objects.select_related('student', 'course').order_by('-overall_score')
    return render(request, 'reports/report_list.html', {'report_cards': report_cards})


@login_required
def report_detail_view(request, pk):
    report = get_object_or_404(ReportCard, pk=pk)
    if not request.user.is_teacher() and report.student != request.user:
        messages.error(request, 'You are not authorized to view this report card.')
        return redirect('/users/report-card/')
    return render(request, 'reports/report_detail.html', {'report': report})


@login_required
def report_edit_view(request, pk):
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can edit report cards.')
        return redirect('report_card')

    report = get_object_or_404(ReportCard, pk=pk)
    if request.method == 'POST':
        form = ReportCardUpdateForm(request.POST, instance=report)
        if form.is_valid():
            report = form.save()
            messages.success(request, 'Report card updated successfully.')
            return redirect('report_detail', pk=report.pk)
    else:
        form = ReportCardUpdateForm(instance=report)
    return render(request, 'reports/report_edit.html', {'form': form, 'report': report})
