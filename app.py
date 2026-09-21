import os
import hmac
import hashlib
import smtplib
from email.message import EmailMessage
from flask import Flask, request, jsonify
from flask_cors import CORS
import razorpay
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_live_Teq4CCRJs0S7li')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'WGrlEoSdWaMsnQ9eplpTDk66')
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'piyush@example.com') # Replace with actual email
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'qbrv unhi pxrf fodn')

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def send_book_email(receiver_email):
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Your copy of Code with Destiny!'
        msg['From'] = SMTP_EMAIL
        msg['To'] = receiver_email
        msg.set_content("Hi there,\n\nThank you for checking out Code with Destiny! Attached is your PDF copy of the book.\n\nHappy reading!\n- Piyush Joshi")

        # Read the PDF file
        pdf_path = os.path.join(os.path.dirname(__file__), 'Code with destiny.pdf')
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            msg.add_attachment(pdf_data, maintype='application', pdf='pdf', filename='Code with destiny.pdf')
        else:
            print("PDF not found at", pdf_path)
            return False

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD.replace(" ", ""))
            smtp.send_message(msg)
        return True
    except Exception as e:
        print("Failed to send email:", e)
        return False

@app.route('/')
def home():
    return "Razorpay & SMTP Backend is Running!"

@app.route('/api/create-order', methods=['POST'])
def create_order():
    try:
        data = request.json or {}
        email = data.get('email')
        # Amount must be passed as an integer (in INR rupees)
        amount_inr = int(data.get('amount', 0))
        
        if amount_inr <= 0:
            if email:
                send_book_email(email)
            return jsonify({'ok': True, 'free': True})
            
        order_amount = amount_inr * 100 # convert to paise
        order_currency = 'INR'
        
        notes = {'description': 'Code with Destiny Book', 'email': email}
        
        order = client.order.create(dict(
            amount=order_amount,
            currency=order_currency,
            notes=notes,
            payment_capture='1'
        ))
        
        return jsonify({
            'orderId': order['id'],
            'amount': order['amount'],
            'currency': order['currency']
        })
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    try:
        data = request.json
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        email = data.get('email')
        
        msg = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode('utf-8'),
            msg.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature == razorpay_signature:
            if email:
                send_book_email(email)
            return jsonify({'ok': True})
        else:
            return jsonify({'error': 'Invalid Signature'}), 400
            
    except Exception as e:
        print(f"Error verifying payment: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
