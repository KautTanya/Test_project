"""
URL configuration for workshop_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from courses import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('courses.urls')), 
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('admin-panel/courses/', views.admin_courses, name='admin_courses'),
    path('admin-panel/modules/<int:module_id>/edit/', views.admin_edit_module, name='admin_edit_module'),
    path('admin-panel/modules/<int:module_id>/delete/', views.admin_delete_module, name='admin_delete_module'),
    path('admin-panel/courses/<int:course_id>/edit/', views.admin_edit_course, name='admin_edit_course'),
    path('admin-panel/courses/<int:course_id>/delete/', views.admin_delete_course, name='admin_delete_course'),
    path('admin-panel/courses/<int:course_id>/add-module/', views.admin_add_module, name='admin_add_module'),
    path('admin-panel/courses/<int:course_id>/duplicate/',views.admin_duplicate_course, name='admin_duplicate_course'),
    path('admin-panel/courses/add/', views.admin_add_course, name='admin_add_course'),
    path('admin-panel/lessons/<int:lesson_id>/edit/', views.admin_edit_lesson, name='admin_edit_lesson'),
    path('admin-panel/lessons/<int:lesson_id>/delete/', views.admin_delete_lesson, name='admin_delete_lesson'),
    path('admin-panel/modules/<int:module_id>/lessons/add/', views.admin_add_lesson, name='admin_add_lesson'),



]

urlpatterns += [
    path("ckeditor/", include("ckeditor_uploader.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)