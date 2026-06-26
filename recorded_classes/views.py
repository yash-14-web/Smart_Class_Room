from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import RecordedClass
from .forms import RecordedClassForm


def _teacher_only(request):
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can manage recorded classes.')
        return redirect('recorded_class_list')
    return None


@login_required
def recorded_class_list_view(request):
    if request.user.is_teacher():
        classes = RecordedClass.objects.filter(
            Q(course__teacher=request.user) | Q(uploaded_by=request.user)
        ).distinct().order_by('-uploaded_at')
    else:
        from courses.models import Enrollment
        enrolled_course_ids = Enrollment.objects.filter(student=request.user, status='approved').values_list('course_id', flat=True)
        classes = RecordedClass.objects.filter(
            course_id__in=enrolled_course_ids
        ).distinct().order_by('-uploaded_at')
    return render(request, 'recorded_classes/recorded_class_list.html', {'classes': classes})


@login_required
def recorded_class_upload_view(request):
    teacher_redirect = _teacher_only(request)
    if teacher_redirect:
        return teacher_redirect

    if request.method == 'POST':
        form = RecordedClassForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            recorded_class = form.save(commit=False)
            recorded_class.uploaded_by = request.user
            recorded_class.save()
            messages.success(request, 'Recorded class uploaded successfully.')
            return redirect('recorded_class_list')
    else:
        form = RecordedClassForm(user=request.user)
    return render(request, 'recorded_classes/recorded_class_form.html', {
        'form': form,
        'page_title': 'Upload Recorded Class',
        'submit_label': 'Upload Class',
    })


@login_required
def recorded_class_edit_view(request, pk):
    teacher_redirect = _teacher_only(request)
    if teacher_redirect:
        return teacher_redirect

    recorded_class = get_object_or_404(RecordedClass, pk=pk)
    
    if recorded_class.uploaded_by != request.user and (recorded_class.course and recorded_class.course.teacher != request.user):
        messages.error(request, 'You do not have permission to edit this recorded class.')
        return redirect('recorded_class_list')

    if request.method == 'POST':
        form = RecordedClassForm(request.POST, request.FILES, instance=recorded_class, user=request.user)
        if form.is_valid():
            recorded_class = form.save(commit=False)
            recorded_class.save()
            messages.success(request, 'Recorded class updated successfully.')
            return redirect('recorded_class_list')
    else:
        form = RecordedClassForm(instance=recorded_class, user=request.user)
    return render(request, 'recorded_classes/recorded_class_form.html', {
        'form': form,
        'page_title': 'Edit Recorded Class',
        'submit_label': 'Save Changes',
        'recorded_class': recorded_class,
    })


@login_required
def recorded_class_delete_view(request, pk):
    teacher_redirect = _teacher_only(request)
    if teacher_redirect:
        return teacher_redirect

    recorded_class = get_object_or_404(RecordedClass, pk=pk)
    
    if recorded_class.uploaded_by != request.user and (recorded_class.course and recorded_class.course.teacher != request.user):
        messages.error(request, 'You do not have permission to delete this recorded class.')
        return redirect('recorded_class_list')

    if request.method == 'POST':
        recorded_class.delete()
        messages.success(request, 'Recorded class deleted successfully.')
        return redirect('recorded_class_list')
    return render(request, 'recorded_classes/recorded_class_confirm_delete.html', {
        'recorded_class': recorded_class,
    })


@login_required
def recorded_class_detail_view(request, pk):
    recorded_class = get_object_or_404(RecordedClass, pk=pk)
    
    if request.user.is_student():
        if not recorded_class.course:
            messages.error(request, 'You do not have access to this recorded class.')
            return redirect('recorded_class_list')
        from courses.models import Enrollment
        is_enrolled = Enrollment.objects.filter(student=request.user, course=recorded_class.course, status='approved').exists()
        if not is_enrolled:
            messages.error(request, 'You must be enrolled in the course to view this recording.')
            return redirect('recorded_class_list')
                
    return render(request, 'recorded_classes/recorded_class_detail.html', {'recorded_class': recorded_class})
