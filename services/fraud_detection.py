import pickle
import numpy as np
import math
from flask import session,request
from database import mysql
from datetime import datetime



# Load models once
global_model = pickle.load(open('models/global_model.pkl', 'rb'))
local_model = pickle.load(open('models/local_model.pkl', 'rb'))


global_label_encoders = pickle.load(open('models/global_label_encoders.pkl', 'rb'))
global_freq_encoders = pickle.load(open('models/global_freq_encoders.pkl', 'rb'))

local_label_encoders = pickle.load(open('models/local_label_encoders.pkl', 'rb'))
local_freq_encoders = pickle.load(open('models/local_freq_encoders.pkl', 'rb'))


# Haversine distance for geolocation
def haversine(lat1, lon1, lat2, lon2):
    # Radius of Earth in km
    R = 6371.0
    # Convert to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # Distance in km


# Local layer rule-based fraud detection
def local_layer_predict(transaction, user_profile, last_txn=None):
    rules_triggered = []

    if last_txn:
        dist = haversine(
            transaction['latitude'], transaction['longitude'],
            last_txn['latitude'], last_txn['longitude']
        )
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


# Dummy encoder
def encode_dummy(x):
    return hash(x) % 1000 if isinstance(x, str) else x


# Encoder
def encode_features(input_dict, label_encoders, freq_encoders):
    encoded = []
    for key, val in input_dict.items():
        if key in label_encoders:
            le = label_encoders[key]
            try:
                encoded_val = le.transform([val])[0]
            except:
                encoded_val = -1
            encoded.append(encoded_val)
        elif key in freq_encoders:
            encoded.append(freq_encoders[key].get(val, 0))
        else:
            try:
                encoded.append(float(val))
            except:
                encoded.append(hash(val) % 1000)
    return np.array([encoded])



# 🔍 Main detection function
# Main detection function
def detect_fraud(form, profile):


    # Example: get timestamp from form or use current time
    timestamp_str = form.get('timestamp') or datetime.now().isoformat()
    txn_time = datetime.fromisoformat(timestamp_str)

    hour = txn_time.hour
    minute = txn_time.minute
    day_of_week = txn_time.weekday()  # 0=Monday, 6=Sunday
    is_night = 1 if hour < 6 or hour > 22 else 0

    # Build input for global model
    global_input_dict = {
    'AMOUNT': float(form['amount']),
    'TRANSACTION_TYPE': form['transaction_type'],
    'PAYER_VPA_FE': form['payer_vpa_fe'],
    'BENEFICIARY_VPA_FE': form['beneficiary_vpa_fe'],
    'PAYER_ACCOUNT_FE': form['payer_account_fe'],
    'BENEFICIARY_ACCOUNT_FE': form['beneficiary_account_fe'],
    'PAYER_IFSC_FE': form['payer_ifsc_fe'],
    'BENEFICIARY_IFSC_FE': form['beneficiary_ifsc_fe'],
    'DEVICE_ID_FE': encode_dummy(request.headers.get('User-Agent', 'Unknown')),
    'IP_ADDRESS_FE': encode_dummy(request.remote_addr),
    'BENEFICIARY_CODE_FE': form.get('beneficiary_code_fe', 'NA'),  # default if missing
    'DAY_OF_WEEK': day_of_week,
    'HOUR': hour,
    'MINUTE': minute,
    'IS_NIGHT': is_night
}
    

    # Local model input
    local_input_dict = {
    'AMOUNT': float(form['amount']),
    'TRANSACTION_TYPE': form['transaction_type'],
    'PAYMENT_INSTRUMENT': form['payment_instrument'],
    'LATITUDE': float(profile.get('home_lat', 0.0)),
    'LONGITUDE': float(profile.get('home_lon', 0.0)),
    'DISTANCE_FROM_LAST_LOCATION': haversine(
    float(profile['home_lat']),
    float(profile['home_lon']),
    float(profile['txn_lat']),
    float(profile['txn_lon'])
),
    'DAY_OF_WEEK': day_of_week,  # from timestamp
    'HOUR': hour,                # from timestamp
    'MINUTE': minute,            # from timestamp
    'IS_NIGHT': is_night,        # 1 if hour in [0-6, 22-23], else 0
    'DEVICE_ID_FE': profile['device_id'],  # assumed pre-encoded
    'IP_ADDRESS_FE': encode_dummy(request.remote_addr),  # assumed pre-encoded
    'BENEFICIARY_VPA_FE': form['beneficiary_vpa_fe'],  # encoded
    'BENEFICIARY_ACCOUNT_FE': form['beneficiary_account_fe']  # encoded
}

    X_global = encode_features(global_input_dict, global_label_encoders, global_freq_encoders)

    X_local = encode_features(local_input_dict, local_label_encoders, local_freq_encoders)

    global_score = global_model.predict_proba(X_global)[0][1]
    score = local_model.decision_function(X_local)[0]
    local_score = -score

    last_txn = {
        'latitude': profile.get('last_txn_lat', profile['home_lat']),
        'longitude': profile.get('last_txn_lon', profile['home_lon']),
    }

    transaction = {
        'amount': float(form['amount']),
        'latitude': float(profile['txn_lat']),
        'longitude': float(profile['txn_lon']),
         'device_id': profile['device_id'],
        'beneficiary_account': form['beneficiary_account_fe'],
        'failed_attempts': int(form.get('failed_attempts', 0))
    }

    user_profile = {
        'known_devices': profile['known_devices'].split(','),
        'known_beneficiaries': profile['known_beneficiaries'].split(',') if profile.get('known_beneficiaries') else [],
        'payment_limit': float(profile['amount']),
        'mean_amount': float(form['amount'])
    }

    local_layer_pred, rules_triggered = local_layer_predict(transaction, user_profile, last_txn)
    final_score = (global_score + local_score) / 2
    final_prediction = int(round(final_score))

    return {
        'global_score': global_score,
        'local_score': local_score,
        'rule_score': local_layer_pred,
        'rules_triggered': rules_triggered,
        'final_score': round(final_score, 2),
        'final_prediction': final_prediction
    }





