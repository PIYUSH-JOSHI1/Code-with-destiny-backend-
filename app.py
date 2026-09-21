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
        msg['Subject'] = 'Your copy of Code with Destiny is here! 🎉'
        msg['From'] = SMTP_EMAIL
        msg['To'] = receiver_email
        
        # Plain text fallback
        msg.set_content("Hi there,\n\nThank you for getting Code with Destiny! You can download your PDF copy here:\nhttps://drive.google.com/drive/folders/1ntZKalqXrz8hK3FW6GSNzfENu_vi5tOJ?usp=drive_link\n\nHappy reading!\n- Piyush Joshi")

        # HTML Email Template
        html_template = """
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 20px;">
              <h2 style="color: #d9a054; font-family: Georgia, serif;">Code with Destiny</h2>
            </div>
            <p>Hi there,</p>
            <p>Thank you so much for your support and for grabbing a copy of <strong>Code with Destiny</strong>!</p>
            <p>You can download the full PDF version of the book securely from Google Drive using the link below:</p>
            <div style="text-align: center; margin: 30px 0;">
              <a href="https://drive.google.com/drive/folders/1ntZKalqXrz8hK3FW6GSNzfENu_vi5tOJ?usp=drive_link" style="background-color: #171310; color: #dcd4c3; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; border: 1px solid #d9a054;">Download PDF Book</a>
            </div>
            <p>I hope you enjoy reading about the late-night coding sessions, canteen classes, and last-minute programs!</p>
            <p>Happy coding,<br><strong>Piyush Joshi</strong></p>
          </body>
        </html>
        """
        
        msg.add_alternative(html_template, subtype='html')

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

@app.route('/api/restore-access', methods=['POST'])
def restore_access():
    try:
        data = request.json or {}
        payment_id = data.get('paymentId')
        
        if not payment_id or not payment_id.startswith('pay_'):
            return jsonify({'error': 'Invalid Payment ID. It must start with pay_'}), 400
            
        # Fetch payment details from Razorpay
        payment = client.payment.fetch(payment_id)
        
        if payment and payment.get('status') in ['captured', 'authorized']:
            return jsonify({'unlocked': True})
        else:
            return jsonify({'error': 'Payment found, but it was not successful.'}), 400
            
    except Exception as e:
        print(f"Error restoring access: {str(e)}")
        return jsonify({'error': 'We could not find that Payment ID. Please check and try again.'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
