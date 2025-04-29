import json
import hmac
import hashlib

from django.shortcuts       import render, redirect
from django.http            import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from .wayforpay     import create_payment, MERCHANT_SECRET_KEY
from .models        import Payment, UserCourse

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

    # 3) Якщо оплата пройшла — оновлюємо UserCourse.is_paid
    if payload['transactionStatus'] == 'Approved':
        uc = UserCourse.objects.filter(order_reference=payload['orderReference']).first()
        if uc:
            uc.is_paid = True
            uc.save()

    print("PAYMENT CALLBACK PAYLOAD:", payload)

    print("Payment processed successfully")
    # 4) Відповідаємо 200 OK
    return HttpResponse("OK")

def register(request):
    return render(request, 'courses/register.html')