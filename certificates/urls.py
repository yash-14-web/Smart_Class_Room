from django.urls import path
from . import views

urlpatterns = [
    path('course/<int:course_pk>/issue/', views.issue_certificate,        name='issue_certificate'),
    path('my/',                           views.my_certificates,          name='my_certificates'),
    path('<int:cert_pk>/view/',           views.view_certificate,         name='view_certificate'),
    path('<int:cert_pk>/download/',       views.download_certificate_pdf, name='download_certificate_pdf'),
    path('<int:cert_pk>/exact/',          views.certificate_exact_view,   name='certificate_exact_view'),
    path('<int:cert_pk>/exact/download/', views.download_certificate_exact_pdf, name='download_certificate_exact_pdf'),
]
