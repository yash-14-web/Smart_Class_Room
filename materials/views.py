from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
from .models import Material
from .forms import MaterialForm
from courses.models import Course, Enrollment
import os

@login_required
def material_upload(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, teacher=request.user)
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.course = course
            material.uploaded_by = request.user
            material.save()
            messages.success(request, f'"{material.title}" uploaded successfully!')
            return redirect('course_detail', pk=course_pk)
    else:
        form = MaterialForm()
    return render(request, 'materials/material_form.html', {'form': form, 'course': course})

@login_required
def material_download(request, pk):
    material = get_object_or_404(Material, pk=pk)
    user = request.user
    is_teacher = material.course.teacher == user
    is_enrolled = Enrollment.objects.filter(student=user, course=material.course).exists()
    if not is_teacher and not is_enrolled:
        messages.error(request, 'You do not have access to this file.')
        return redirect('course_list')
    try:
        response = FileResponse(material.file.open('rb'), as_attachment=True, filename=material.filename())
        return response
    except FileNotFoundError:
        raise Http404("File not found.")

@login_required
def material_delete(request, pk):
    material = get_object_or_404(Material, pk=pk, course__teacher=request.user)
    course_pk = material.course.pk
    if request.method == 'POST':
        material.file.delete(save=False)
        material.delete()
        messages.success(request, 'Material deleted successfully.')
        return redirect('course_detail', pk=course_pk)
    return render(request, 'materials/material_confirm_delete.html', {'material': material})
