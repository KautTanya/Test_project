import json
import hmac
import hashlib
import secrets
import time
from collections import defaultdict
from django.shortcuts       import render, redirect, get_object_or_404
from django.http            import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Prefetch
from django.forms import modelformset_factory
from django.forms import inlineformset_factory
from .wayforpay     import create_payment, MERCHANT_SECRET_KEY
from .models        import Payment, UserCourse, Course, Module, Lesson, LessonProgress
from .forms import CourseForm, ModuleFormSet, LessonFormSet, ModuleForm, LessonForm, ContentBlockFormSet, ContentBlock, ContentBlockForm

def index(request):
    """
    Головна сторінка з формою для введення email та кнопкою 'Оплатити'.
    """
    return render(request, 'courses/index.html')


def start_payment(request):
    """
    Отримує email через POST, створює платіж у WayForPay і
    редіректить користувача на сторінку оплати.
    """
    if request.method != 'POST':
        return redirect('index')

    email = request.POST.get('email')
    course_id = request.POST.get('course_id')

    if not email or not course_id:
        return redirect('index')

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return redirect('index')

    try:
        # Створюємо платіж та отримуємо URL
        payment_url, order_reference = create_payment(email=email, amount=course.price, course_name=course.title)

        if request.user.is_authenticated:
            UserCourse.objects.create(
                user=request.user,
                course=course,
                order_reference=order_reference,
                is_paid=False  # підтвердимо після колбеку
            )
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
        return HttpResponseBadRequest("Only POST allowed")

    try:
        payload = json.loads(request.body)
        print("Callback payload:", payload)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    # 1. Перевірка підпису
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

    # 2. Оновлюємо або створюємо запис про оплату
    Payment.objects.update_or_create(
        order_reference=payload['orderReference'],
        defaults={
            'amount': payload['amount'],
            'currency': payload['currency'],
            'status': payload['transactionStatus'],
            'response_data': payload,
        }
    )

    # 3. Якщо платіж успішний
    if payload['transactionStatus'] == 'Approved':
        order_ref = payload['orderReference']
        email = payload.get('email')
        product_name = payload.get('productName', [''])[0].strip()
        course = Course.objects.filter(title__iexact=product_name).first()

        if not course:
            print(f"Course not found: {product_name}")
            return HttpResponse("Course not found")

        # Якщо є запис UserCourse — просто оновлюємо
        uc = UserCourse.objects.filter(order_reference=order_ref).first()
        if uc:
            uc.is_paid = True
            uc.save()
        else:
            # Якщо користувача ще немає — створюємо
            if email:
                user, created = User.objects.get_or_create(username=email, defaults={'email': email})
                if created:
                    password = secrets.token_urlsafe(10)
                    user.set_password(password)
                    user.save()

                    # Надсилаємо пароль
                    send_mail(
                        subject='Доступ до курсу',
                        message=f'''Вітаємо!\n\nВаш акаунт створено.\nЛогін: {email}\nПароль: {password}\n\nУвійти: http://localhost:8000/login/''',
                        from_email='no-reply@example.com',
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    print(f"User {email} created and password sent.")

                # Прив'язуємо курс
                UserCourse.objects.get_or_create(
                    user=user,
                    course=course,
                    defaults={'order_reference': order_ref, 'is_paid': True}
                )

                # Якщо цей запит від авторизованого користувача — виводимо повідомлення і редіректимо
                if request.user.is_authenticated:
                    messages.success(request, 'Оплата пройшла успішно. Доступ до курсу відкрито!')
                    return redirect('cabinet')

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
    if request.user.is_superuser:
        # Адміну показуємо всі курси без фільтрації
        courses = Course.objects.all()
        return render(request, 'courses/cabinet.html', {
            'all_courses': courses,
            'user_courses': None,
        })
    else:
        user_courses = UserCourse.objects.filter(user=request.user, is_paid=True).select_related('course')
        return render(request, 'courses/cabinet.html', {
            'all_courses': None,
            'user_courses': user_courses,
        })


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = course.modules.all().order_by('order').prefetch_related(
        Prefetch('lessons', queryset=Lesson.objects.order_by('order'))
    )

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
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.module.course

    progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

    # Знайдемо попередній і наступний урок у межах курсу
    lessons = Lesson.objects.filter(module__course=lesson.module.course).order_by('module__order', 'order')
    lesson_list = list(lessons)
    current_index = lesson_list.index(lesson)

    prev_lesson = lesson_list[current_index - 1] if current_index > 0 else None
    next_lesson = lesson_list[current_index + 1] if current_index < len(lesson_list) - 1 else None

    # Позначення уроку як виконаного
    if request.method == 'POST' and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save()
        return redirect('lesson_detail', lesson_id=lesson.id)
    
    lessons_progress = LessonProgress.objects.filter(
        user=request.user,
        lesson__module__course=lesson.module.course,
        is_completed=True
    ).values_list('lesson_id', flat=True)

    available_lessons_ids = []
    unlocked = True
    for m in course.modules.all().order_by('order'):
        for l in m.lessons.all().order_by('order'):
            if unlocked:
                available_lessons_ids.append(l.id)
            if l.id not in lessons_progress:
                unlocked = False

    if lesson.id not in available_lessons_ids:
        messages.warning(request, 'Цей урок ще недоступний. Завершіть попередні.')
        return redirect('course_detail', course_id=course.id)

    next_lesson_available = next_lesson and next_lesson.id in available_lessons_ids

    modules = course.modules.prefetch_related(
        Prefetch('lessons', queryset=Lesson.objects.order_by('order'))
    ).order_by('order')

    return render(request, 'courses/lesson_detail.html', {
        'lesson': lesson,
        'progress': progress,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson if next_lesson_available else None,
        'modules': modules,
        'course': course,
        'current_lesson_id': lesson.id,
        'available_lessons_ids': available_lessons_ids,
    })

def course_landing(request, slug):
    course = get_object_or_404(Course, slug=slug)
    user_courses = []
    if request.user.is_authenticated:
        user_courses = UserCourse.objects.filter(user=request.user, is_paid=True).values_list('course_id', flat=True)

    return render(request, 'courses/course_landing.html', {
        'course': course,
        'user_courses': user_courses
    })

def index(request):
    courses = Course.objects.filter(is_published=True)
    return render(request, 'courses/index.html', {'courses': courses})

@staff_member_required
def admin_dashboard(request):
    total_courses = Course.objects.count()
    published_courses = Course.objects.filter(is_published=True).count()
    active_users = UserCourse.objects.values('user').distinct().count()

    return render(request, 'admin_panel/dashboard.html', {
        'total_courses': total_courses,
        'published_courses': published_courses,
        'active_users': active_users,
    })

@staff_member_required
def admin_courses(request):
    courses = Course.objects.all()
    return render(request, 'admin_panel/courses.html', {'courses': courses})

@staff_member_required
def admin_edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        course.title = request.POST.get('title')
        course.price = request.POST.get('price')
        course.is_published = 'is_published' in request.POST
        course.save()
        return redirect('admin_courses')

    return render(request, 'admin_panel/edit_course.html', {'course': course})

@staff_member_required
def admin_edit_module(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    LessonFormSet = inlineformset_factory(Module, Lesson, form=LessonForm, extra=1, can_delete=True)

    if request.method == 'POST':
        module_form = ModuleForm(request.POST, instance=module)
        lesson_formset = LessonFormSet(request.POST, instance=module)

        if module_form.is_valid() and lesson_formset.is_valid():
            module_form.save()
            lessons = lesson_formset.save(commit=False)

            for lesson in lessons:
                lesson.module = module
                lesson.save()

            # Збереження контенту для кожного уроку
            for form in lesson_formset.forms:
                lesson = form.instance
                prefix = f'block-{lesson.id if lesson.id else "__new__"}'
                ContentFormSet = inlineformset_factory(Lesson, ContentBlock, form=ContentBlockForm, extra=1, can_delete=True)
                content_formset = ContentFormSet(request.POST, request.FILES, instance=lesson, prefix=prefix)
                if content_formset.is_valid():
                    content_formset.save()

            return redirect('admin_edit_course', course_id=module.course.id)
    else:
        module_form = ModuleForm(instance=module)
        lesson_formset = LessonFormSet(instance=module)

    # Для GET-запиту — підготовка formsets для кожного уроку
    lesson_formsets = []
    for form in lesson_formset.forms:
        lesson = form.instance
        ContentFormSet = inlineformset_factory(Lesson, ContentBlock, form=ContentBlockForm, extra=1, can_delete=True)
        prefix = f'block-{lesson.id if lesson.id else "__new__"}'
        content_formset = ContentFormSet(instance=lesson, prefix=prefix)
        lesson_formsets.append((form, content_formset))

    return render(request, 'admin_panel/edit_module.html', {
        'module_form': module_form,
        'lesson_formsets': lesson_formsets,
        'module': module,
    })


@staff_member_required
def admin_edit_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    block_formset = ContentBlockFormSet(request.POST or None, instance=lesson)

    if request.method == 'POST':
        if block_formset.is_valid():
            block_formset.save()
            return redirect('admin_edit_module', module_id=lesson.module.id)

    return render(request, 'admin_panel/edit_lesson.html', {
        'lesson': lesson,
        'block_formset': block_formset,
    })

@staff_member_required
def admin_delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course.delete()
    return redirect('admin_courses')

@staff_member_required
def admin_duplicate_course(request, course_id):
    original = get_object_or_404(Course, id=course_id)

    new_title = f"{original.title} (копія)"
    new_slug = slugify(new_title)

    # Гарантуємо унікальність slug
    base_slug = new_slug
    counter = 1
    while Course.objects.filter(slug=new_slug).exists():
        new_slug = f"{base_slug}-{counter}"
        counter += 1

    new_course = Course(
        title=new_title,
        price=original.price,
        is_published=False,
        description=original.description
    )
    new_course.save()

    for module in original.modules.all():
        new_module = Module.objects.create(
            title=module.title,
            order=module.order,
            course=new_course
        )

        for lesson in module.lessons.all():
            Lesson.objects.create(
                title=lesson.title,
                content=lesson.content,
                order=lesson.order,
                module=new_module
            )


    return redirect('admin_courses')

@staff_member_required
def admin_delete_module(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    course_id = module.course.id
    module.delete()
    return redirect('admin_edit_course', course_id=course_id)


@staff_member_required
def admin_add_course(request):
    if request.method == 'POST':
        course_form = CourseForm(request.POST)
        module_formset = ModuleFormSet(request.POST, prefix='modules')

        if course_form.is_valid() and module_formset.is_valid():
            course = course_form.save()
            module_formset.instance = course
            modules = module_formset.save(commit=False)

            for module in modules:
                module.course = course
                module.save()

                # Тепер обробляємо formset уроків для кожного модуля
                lesson_prefix = f'lessons-{module.id}'
                lesson_formset = LessonFormSet(request.POST or None, instance=module, prefix=lesson_prefix)

                if lesson_formset.is_valid():
                    lesson_formset.save()
                else:
                    print("LessonFormSet errors:", lesson_formset.errors)

            return redirect('admin_courses')
    else:
        course_form = CourseForm()
        module_formset = ModuleFormSet(prefix='modules')

    return render(request, 'admin_panel/add_course.html', {
        'course_form': course_form,
        'module_formset': module_formset,
    })

@staff_member_required
def admin_add_module(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        # description = request.POST.get('description')
        last_order = Module.objects.filter(course=course).count()

        if title:
            Module.objects.create(
                course=course,
                title=title,
                order=last_order + 1
            )
            return redirect('admin_edit_course', course_id=course.id)

    return render(request, 'admin_panel/add_module.html', {'course': course})
