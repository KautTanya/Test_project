from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='courses/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register, name='register'),
    path('start_payment/', views.start_payment, name='start_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('test-email/', views.test_email, name='test_email'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='courses/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='courses/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='courses/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='courses/password_reset_complete.html'), name='password_reset_complete'),
    path('cabinet/', login_required(views.cabinet_view), name='cabinet'),
    path('course/<slug:slug>/', views.course_landing, name='course_landing'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('contact/', views.contact_view, name='contact'),
]
