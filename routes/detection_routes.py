from database import mysql
from services.fraud_detection import detect_fraud,global_label_encoders
from services.fake_customer_service import detect_fake_customer_care
from flask import render_template,request,Blueprint,session
from services.qr_scam_service import process_qr_image
from datetime import datetime



detection_bp = Blueprint('detection', __name__)



@detection_bp.route('/detect/fraud', methods=['GET'])
def fraud_input_form():
    return render_template('fraud_form.html')  # create this template


@detection_bp.route('/detect/fake-care')
def fake_care_input():
    return render_template('fake_customer.html')


@detection_bp.route('/detect/qr-scam')
def qr_code_input_form():
    return render_template('qr_code.html')


@detection_bp.route('/run-fraud-check', methods=['POST'])
def run_fraud_check():
    form = request.form.to_dict()
    phone = form.get('phone')

    if not phone:
        return "Phone number is required", 400

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM profile_form WHERE phone = %s", (phone,))
    profile = cursor.fetchone()
    cursor.close()

    if not profile:
        return "User profile not found", 400
    

    def encode_field(encoders,field_name, value):
        try:
            return encoders[field_name].transform([value])[0]
        except:
            return -1
        
    form['payer_vpa_fe'] = encode_field(global_label_encoders, 'PAYER_VPA', form.get('payer_vpa', ''))
    form['beneficiary_vpa_fe'] = encode_field(global_label_encoders, 'BENEFICIARY_VPA', form.get('beneficiary_vpa', ''))
    form['payer_account_fe'] = encode_field(global_label_encoders, 'PAYER_ACCOUNT', form.get('payer_account', ''))
    form['beneficiary_account_fe'] = encode_field(global_label_encoders, 'BENEFICIARY_ACCOUNT', form.get('beneficiary_account', ''))
    form['payer_ifsc_fe'] = encode_field(global_label_encoders, 'PAYER_IFSC', form.get('payer_ifsc', ''))
    form['beneficiary_ifsc_fe'] = encode_field(global_label_encoders, 'BENEFICIARY_IFSC', form.get('beneficiary_ifsc', ''))




    result = detect_fraud(form, profile)

    return render_template("fraud_result.html", result=result)






#Fake Customer Care

@detection_bp.route('/run-fake-care-detection', methods=['POST'])
def run_fake_care_check():
    form = request.form
    result = detect_fake_customer_care(form)
    return render_template('fake_customer_result.html', result=result)



#QR

@detection_bp.route('/run-qr-detection', methods=['POST'])
def run_qr_detection():
    if 'qr_image' not in request.files:
        return "No image uploaded", 400

    qr_image = request.files['qr_image']
    
    if qr_image.filename == '':
        return "No selected image", 400

    # Call your QR scam prediction service
    result = process_qr_image(qr_image)

    return render_template('qr_result.html', result=result)

