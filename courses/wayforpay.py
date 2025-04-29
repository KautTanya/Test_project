import hmac, hashlib
import json
import requests
import time

# Конфігурація Wayforpay
# MERCHANT_ACCOUNT = 'test_merch_n1'
# MERCHANT_SECRET_KEY = 'flk3409refn54t54t*FNJRET'
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
    
    # Створюємо підпис
    return hmac.new(
        MERCHANT_SECRET_KEY.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.md5
    ).hexdigest()

def create_payment(email, amount=149, currency='UAH'):
    order_reference = str(int(time.time()))
    order_date = int(time.time())
    domain_name = '08f9-94-124-166-101.ngrok-free.app'

    data = {
        "transactionType": "CREATE_INVOICE",
        "apiVersion": 1,
        "merchantAccount": MERCHANT_ACCOUNT,
        "merchantDomainName": domain_name,
        "merchantAuthType": "SimpleSignature",  
        "orderReference": order_reference,
        "orderDate": order_date,
        "amount": amount,
        "currency": currency,
        "productName": ["Workshop"],
        "productCount": [1],
        "productPrice": [amount],
        "clientEmail": email,
        "language": "UA",

        "returnUrl": f"https://{domain_name}/",
        "serviceUrl": f"https://{domain_name}/payment/callback/",
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
            return response_data['invoiceUrl']
        else:
            raise Exception(f"Wayforpay error: {response_data.get('reasonCode')} - {response_data.get('reason')}")
    else:
        raise Exception(f"HTTP error: {response.status_code}")

