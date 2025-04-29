import hmac
import hashlib
import json
import requests
import time

# Константи
MERCHANT_ACCOUNT = "127_0_0_142"
MERCHANT_SECRET_KEY = "0234270dd4d20bec802fcacca64d75040a867c5b"
NGROK_DOMAIN = "a47f-94-124-166-101.ngrok-free.app"

def generate_signature(merchant_account, order_reference, amount, currency, transaction_status, reason_code):
    sign_parts = [
        merchant_account,
        order_reference,
        str(amount),
        currency,
        transaction_status,
        str(reason_code),
    ]
    sign_string = ';'.join(sign_parts)
    signature = hmac.new(
        MERCHANT_SECRET_KEY.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.md5
    ).hexdigest()
    return signature

def send_callback(order_reference, amount, currency="UAH", transaction_status="Approved", reason_code=1100):
    signature = generate_signature(
        MERCHANT_ACCOUNT,
        order_reference,
        amount,
        currency,
        transaction_status,
        reason_code
    )

    payload = {
        "merchantAccount": MERCHANT_ACCOUNT,
        "orderReference": order_reference,
        "amount": amount,
        "currency": currency,
        "transactionStatus": transaction_status,
        "reasonCode": reason_code,
        "merchantSignature": signature
    }

    url = f"https://{NGROK_DOMAIN}/payment/callback/"
    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    print("\n========== Результат ==========")
    print("Status Code:", response.status_code)
    try:
        print("Response JSON:", json.dumps(response.json(), indent=2))
    except Exception:
        print("Response Text:", response.text)
    print("================================")

    # Запис в лог (опціонально)
    with open("callback_log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n--- Запит на {time.ctime()} ---\n")
        f.write(f"OrderReference: {order_reference}\n")
        f.write(f"Amount: {amount}\n")
        f.write(f"Currency: {currency}\n")
        f.write(f"TransactionStatus: {transaction_status}\n")
        f.write(f"Відповідь сервера: {response.status_code} - {response.text}\n")
        f.write(f"===============================\n")


if __name__ == "__main__":
    print("=== Надсилання тестового Callback на WayForPay ===")
    order_reference = input("Введіть orderReference (наприклад TEST_APPROVED_12345): ").strip()
    amount = float(input("Введіть суму платежу (наприклад 149): ").strip())
    currency = input("Введіть валюту (UAH або USD, або інша) [за замовчуванням UAH]: ").strip() or "UAH"
    status = input("Введіть статус транзакції (Approved / Declined) [за замовчуванням Approved]: ").strip() or "Approved"

    send_callback(order_reference, amount, currency, status)

# python send_callback.py