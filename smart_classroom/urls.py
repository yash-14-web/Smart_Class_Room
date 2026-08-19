from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from users import views as user_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('courses/', include('courses.urls')),
    path('assignments/', include('assignments.urls')),
    path('chat/', include('chat.urls')),     
    path('materials/', include('materials.urls')),
    path('quiz/', include('quiz.urls')),
    path('tests/', include('tests.urls')),
    path('certificates/', include('certificates.urls')),
    path('projects/', include('projects.urls')),
    path('recorded-classes/', include('recorded_classes.urls')),
    path('reports/', include('reports.urls')),
    path('attendance/', include('attendance.urls')),
    path('', user_views.landing_page_view, name='landing_page'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
