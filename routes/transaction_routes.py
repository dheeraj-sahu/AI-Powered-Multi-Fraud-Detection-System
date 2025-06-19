from flask import Blueprint, request, render_template,session
from database import mysql
from utils.fraud_rules import detect_fraud

tx_bp = Blueprint('transaction', __name__)

@tx_bp.route('/transaction',methods=['GET','POST'])
def transaction():
    if request.method == 'POST':
        email = session.get('email')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user= cur.fetchone()

        tx_fields = [
            'amount', 'transaction_type', 'payment_instrument',
            'beneficiary_vpa', 'beneficiary_account',
            'beneficiary_ifsc', 'initiation_mode'
        ]

        tx = {field: request.form[field] for field in tx_fields}

        tx['amount'] = float(tx['amount'])


        device_id = 'DEVICE123'
        known_devices = ['DEVICE123']
        ip_loc = 'IN'
        prev_loc = 'IN'


        result = detect_fraud(tx, user, device_id, known_devices, ip_loc, prev_loc)


        cur.execute("""
            INSERT INTO transactions (
                user_id, amount, transaction_type, payment_instrument,
                beneficiary_vpa, beneficiary_account, beneficiary_ifsc,
                initiation_mode, status, reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user['id'], tx['amount'], tx['transaction_type'], tx['payment_instrument'],
            tx['beneficiary_vpa'], tx['beneficiary_account'], tx['beneficiary_ifsc'],
            tx['initiation_mode'], result['status'], result['reason']
        ))


        mysql.connection.commit()

        cur.close()


        return f"<h3>Transaction {result['status']} - {result['reason']}</h3><a href='/transaction'>Back</a>"

    return render_template('transaction.html')


@tx_bp.route('/dashboard')
def dashboard():
    email = session.get('email')
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    user = cur.fetchone()

    cur.execute("SELECT * FROM transactions WHERE user_id = %s ORDER BY created_at DESC", (user['id'],))
    txns = cur.fetchall()
    cur.close()

    return render_template('dashboard.html', txns=txns)
