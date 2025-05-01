import hmac, hashlib
import json
import requests
import time
from decimal import Decimal

# Конфігурація Wayforpay
MERCHANT_ACCOUNT = '127_0_0_142'
MERCHANT_SECRET_KEY = '0234270dd4d20bec802fcacca64d75040a867c5b'
WAYFORPAY_API_URL = 'https://api.wayforpay.com/api'

def generate_signature(data):
    # Створюємо список значень для підпису
    sign_parts = []
    sign_parts.append(data['merchantAccount'])
    sign_parts.append(data['merchantDomainName'])
    sign_parts.append(data['orderReference'])
    sign_parts.append(str(data['orderDate']))
    sign_parts.append(str(data['amount']))
    sign_parts.append(data['currency'])
    
    # Додаємо всі продукти окремо
    for product in data['productName']:
        sign_parts.append(product)
    
    # Додаємо всі кількості окремо
    for count in data['productCount']:
        sign_parts.append(str(count))
    
    # Додаємо всі ціни окремо
    for price in data['productPrice']:
        sign_parts.append(str(price))
    
    # З'єднуємо все в один рядок
    sign_string = ';'.join(sign_parts)

    print("SIGN STRING USED FOR SIGNATURE:", sign_string)
    
    # Створюємо підпис
    return hmac.new(
        MERCHANT_SECRET_KEY.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.md5
    ).hexdigest()

def create_payment(email, amount=149, course_name="Workshop", currency='UAH'):
    order_reference = str(int(time.time()))
    order_date = int(time.time())
    domain_name = '8c88-94-124-166-101.ngrok-free.app '

    amount = Decimal(format(amount, '.2f'))

    data = {
        "transactionType": "CREATE_INVOICE",
        "apiVersion": 1,
        "merchantAccount": MERCHANT_ACCOUNT,
        "merchantDomainName": domain_name,
        "merchantAuthType": "SimpleSignature",  
        "orderReference": order_reference,
        "orderDate": order_date,
        "amount": str(amount),
        "currency": currency,
        "productName": [course_name],
        "productCount": [1],
        "productPrice": [str(amount), ],
        "clientEmail": email,
        "language": "UA",

        "returnUrl": f"https://{domain_name}/",
        "serviceUrl": f"https://{domain_name}/payment/callback/",

        # "amount_str": amount_str,
    }

    data['merchantSignature'] = generate_signature(data)

    # Додаємо логування
    print("WayForPay REQUEST:")
    print(json.dumps(data, indent=2))
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(WAYFORPAY_API_URL, headers=headers, data=json.dumps(data))
    
    # Логуємо відповідь
    print("WayForPay RESPONSE:")
    print(response.status_code)
    print(response.text)
    
    if response.status_code == 200:
        response_data = response.json()
        if response_data.get('reasonCode') == 1100:
            return response_data['invoiceUrl'], order_reference
        else:
            raise Exception(f"Wayforpay error: {response_data.get('reasonCode')} - {response_data.get('reason')}")
    else:
        raise Exception(f"HTTP error: {response.status_code}")