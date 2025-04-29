import json
import hmac
import hashlib
import secrets
from collections import defaultdict
from django.shortcuts       import render, redirect, get_object_or_404
from django.http            import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.utils import timezone
from .wayforpay     import create_payment, MERCHANT_SECRET_KEY
from .models        import Payment, UserCourse, Course, Lesson, LessonProgress

def index(request):
    """
    Головна сторінка з формою для введення email та кнопкою 'Оплатити'.
    """
    return render(request, 'courses/index.html')


@csrf_exempt
def start_payment(request):
    """
    Отримує email через POST, створює платіж у WayForPay і
    редіректить користувача на сторінку оплати.
    """
    if request.method != 'POST':
        return redirect('index')

    email = request.POST.get('email')
    if not email:
        return render(request, 'courses/index.html', {
            'error': 'Будь ласка, введіть email.'
        })

    try:
        # Створюємо платіж та отримуємо URL
        payment_url = create_payment(email)
        # Зберігаємо order_reference у UserCourse (поки що без зв'язку з курсом/юзером)
        # Якщо ти створюєш UserCourse у цей момент, тут можна прописати:
        # uc = UserCourse.objects.create(user=request.user, course=Course.objects.get(...), order_reference=order_ref)
        return redirect(payment_url)
    except Exception as e:
        print("Error in create_payment:", e)
        return render(request, 'courses/index.html', {
            'error': 'Не вдалося створити платіж. Спробуйте пізніше.'
        })


@csrf_exempt
def payment_callback(request):
    print("Payment callback received:", request.method)
    if request.method != 'POST':
        print("Only POST allowed")
        return HttpResponseBadRequest("Only POST allowed")
    
    try:
        payload = json.loads(request.body)
        print("Callback payload:", payload)
    except json.JSONDecodeError:
        print("Invalid JSON")
        return HttpResponseBadRequest("Invalid JSON")

    # 1) Перевіряємо HMAC-MD5 підпис колбеку
    sign_list = [
        payload.get('merchantAccount'),
        payload.get('orderReference'),
        str(payload.get('amount')),
        payload.get('currency'),
        payload.get('transactionStatus'),
        str(payload.get('reasonCode')),
    ]
    sign_string = ';'.join(sign_list)
    expected_sig = hmac.new(
        MERCHANT_SECRET_KEY.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.md5
    ).hexdigest()

    if expected_sig != payload.get('merchantSignature'):
        return HttpResponseBadRequest("Invalid signature")

    # 2) Зберігаємо або оновлюємо запис у Payment
    payment, created = Payment.objects.update_or_create(
        order_reference=payload['orderReference'],
        defaults={
            'amount':        payload['amount'],
            'currency':      payload['currency'],
            'status':        payload['transactionStatus'],
            'response_data': payload,
        }
    )

    # 3) Якщо оплата пройшла — оновлюємо UserCourse.is_paid або створюємо користувача
    if payload['transactionStatus'] == 'Approved':
        order_ref = payload['orderReference']
        email = payload.get('email')

        # Перевірка, чи є UserCourse
        uc = UserCourse.objects.filter(order_reference=order_ref).first()
        if uc:
            uc.is_paid = True
            uc.save()
        else:
            if email:
                if not User.objects.filter(username=email).exists():
                    password = secrets.token_urlsafe(10)
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password
                    )
                    print(f"Generated password for {email}: {password}")

                    # Надсилання листа з паролем
                    send_mail(
                        subject='Доступ до курсу',
                        message=f'''Вітаємо!

                                    Ваш акаунт на платформі активовано.

                                    Логін: {email}
                                    Пароль: {password}

                                    Увійти до кабінету можна тут:
                                    http://localhost:8000/login/

                                    Бажаємо приємного навчання!
                                    ''',
                        from_email='no-reply@example.com',
                        recipient_list=[email],
                        fail_silently=False,
                    )

                    print(f"User {email} created. Password sent.")

    print("PAYMENT CALLBACK PAYLOAD:", payload)
    print("Payment processed successfully")
    return HttpResponse("OK")


def register(request):
    return render(request, 'courses/register.html')

def test_email(request):
    send_mail(
        'Тестовий лист від Django',
        'Вітаю! Це тестовий лист, який відправився через SMTP Gmail!',
        'твій_email@gmail.com',    # Відправник
        ['твій_email@gmail.com'],   # Отримувач (можна навіть той самий email)
        fail_silently=False,
    )
    return HttpResponse('Лист надіслано!')

@login_required
def cabinet_view(request):
    user_courses = UserCourse.objects.filter(user=request.user, is_paid=True)
    return render(request, 'courses/cabinet.html', {'user_courses': user_courses})

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = course.modules.all().order_by('order')
    lessons_progress = LessonProgress.objects.filter(
        user=request.user,
        lesson__module__course=course
    )

    completed_lessons_ids = lessons_progress.filter(is_completed=True).values_list('lesson_id', flat=True)

    all_lessons_count = Lesson.objects.filter(module__course=course).count()
    completed_lessons_count = lessons_progress.filter(is_completed=True).count()

    progress = int((completed_lessons_count / all_lessons_count) * 100) if all_lessons_count else 0

    # Створюємо список ID доступних уроків
    available_lessons_ids = []
    unlocked = True
    for module in modules:
        for lesson in module.lessons.all():
            if unlocked:
                available_lessons_ids.append(lesson.id)
            if lesson.id not in completed_lessons_ids:
                unlocked = False  # Блокувати всі наступні

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'modules': modules,
        'completed_lessons_ids': completed_lessons_ids,
        'available_lessons_ids': available_lessons_ids,
        'progress': progress,
    })


@login_required
def lesson_detail(request, lesson_id):
    lesson = Lesson.objects.select_related('module__course').get(id=lesson_id)

    # Перевіряємо, чи є прогрес для цього уроку і користувача
    progress, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )

    if request.method == 'POST':
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save()

    return render(request, 'courses/lesson_detail.html', {
        'lesson': lesson,
        'progress': progress
    })