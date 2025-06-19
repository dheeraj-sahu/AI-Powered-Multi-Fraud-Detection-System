import pickle
import numpy as np
import math
from flask import request, render_template, redirect
from app import app, init_mysql

#Load Models
global_model = pickle.load(open('models/global_model.pkl','rb'))
local_model = pickle.load(open('models/local_model.pkl','rb'))


# Haversine Formula

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)

    a = (
        math.sin(dlat/2)**2 +
        math.cos(math.radians(lat1))*
        math.cos(math.radians(lat2))*
        math.sin(dlon/2)**2
    )

    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))


# Local Layer rule-based logic

def local_layer_predict(transaction,user_profile, last_txn=None):
    rules_triggered =[]

    if last_txn:
        dist = haversine(transaction['latitude'],transaction['longitude'],last_txn['latitude'],last_txn['longitude'])

        if dist > 1500:
            rules_triggered.append("IP/Location Mismatch")

    if transaction['device_id'] not in user_profile['known_devices'] and \
        transaction['amount'] > user_profile['payment_limit']:
        rules_triggered.append("New Device + High Amount")

    if transaction['amount'] > user_profile['payment_limit']:
        rules_triggered.append("Exceeds Payment Limit")

    if transaction['amount'] > 3 * user_profile['mean_amount']:
        rules_triggered.append("Sudden High Amount")

    if transaction['beneficiary_account'] not in user_profile['known_beneficiaries'] and \
       transaction['amount'] > 5000:
        rules_triggered.append("New Beneficiary + High Amount")

    if transaction.get('failed_attempts', 0) > 3:
        rules_triggered.append("Too Many Failed Attempts")

    is_fraud = int(len(rules_triggered) >= 2)
    return is_fraud, rules_triggered



# Main route
@app.route('/run-fraud-check', methods=['POST'])
def run_fraud_check():
    form = request.form
    #Global model input
    global_input = [
        float(form['amount']),
        form['transaction_type'],
        form['payer_vpa_fe'],
        form['beneficiary_vpa_fe'],
        form['payer_account_fe'],
        form['beneficiary_account_fe'],
        form['payer_ifsc_fe'],
        form['beneficiary_ifsc_fe'],
        form['beneficiary_code_fe']
    ]

    # Local model input
    local_input = [
        float(form['amount']),
        form['transaction_type'],
        form['payment_instrument'],
        form['beneficiary_vpa_fe'],
        form['beneficiary_account_fe']
    ]


    # Get user profile from DB
    phone = form.get('phone')
    cursor = init_mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_profiles WHERE phone = %s", (phone,))
    profile = cursor.fetchone()
    cursor.close()

    if not profile:
        return "User profile not found", 400
    

    # Prepare dummy encoder (replace with your actual encoders)
    def encode_dummy(x):
        return hash(x) % 1000 if isinstance(x, str) else x


    X_global = np.array([[encode_dummy(v) for v in global_input]])
    X_local = np.array([[encode_dummy(v) for v in local_input]])


    global_pred = int(global_model.predict(X_global)[0])
    local_pred = int(local_model.predict(X_local)[0])


    # Last transaction (mocked or fetched)
    last_txn = {
        'latitude': profile.get('last_txn_lat', profile['home_lat']),
        'longitude': profile.get('last_txn_lon', profile['home_lon']),
    }


    # Construct local layer inputs
    transaction = {
        'amount': float(form['amount']),
        'latitude': float(profile['txn_lat']),
        'longitude': float(profile['txn_lon']),
        'device_id': form['device_id'],
        'beneficiary_account': form['beneficiary_account_fe'],
        'failed_attempts': int(form.get('failed_attempts', 0))
    }


    user_profile = {
        'known_devices': profile['known_devices'].split(','),
        'known_beneficiaries': profile['known_beneficiaries'].split(',') if profile.get('known_beneficiaries') else [],
        'payment_limit': float(profile['payment_limit']),
        'mean_amount': float(profile['mean_amount'])
    }


    local_layer_pred, rules_triggered = local_layer_predict(transaction, user_profile, last_txn)


    # Final ensemble
    final_score = (global_pred + local_pred + local_layer_pred) / 3
    final_prediction = int(round(final_score))



    return render_template("fraud_result.html",
                           global_pred=global_pred,
                           local_pred=local_pred,
                           local_layer_pred=local_layer_pred,
                           rules_triggered=rules_triggered,
                           final_prediction=final_prediction)



    