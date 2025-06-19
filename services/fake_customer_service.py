import pickle
import joblib
import numpy as np

fake_care_model = pickle.load(open('models/Fake_Customer.pkl', 'rb'))

le_1 = joblib.load('models/le_1_day_name.pkl')      
le_2 = joblib.load('models/le_2_is_weekend.pkl')  
le_3 = joblib.load('models/le_3_destination.pkl') 
le_4 = joblib.load('models/le_4_time_category.pkl')
le_5 = joblib.load('models/le_5_caller_status.pkl')
le_6 = joblib.load('models/le_6_number_pattern.pkl') 
le_7 = joblib.load('models/le_7_operator.pkl')  


def detect_fake_customer_care(form):
    """
    Predict if a customer care call is fake using the pre-trained model
    and the same LabelEncoders used during training.
    """
    try:
        day_name_code    = le_1.transform([form['Day_Name']])[0]
        is_weekend_code  = le_2.transform([form['Is_Weekend']])[0]
        dest_code        = le_3.transform([form['Destination_Type']])[0]
        time_code        = le_4.transform([form['Time_Category']])[0]
        caller_code      = le_5.transform([form['Caller_ID_Status']])[0]
        pattern_code     = le_6.transform([form['Number_Pattern']])[0]
        op_code          = le_7.transform([form['Operator']])[0]

        day_of_week      = int(form['Day_of_Week'])
        hour             = int(form['Hour'])
        call_duration    = float(form['Call_Duration_Minutes'])
        call_cost        = float(form.get('Call_Cost_USD', 0.0))
        cost_per_minute  = float(form.get('Cost_Per_Minute', 0.0))
        daily_count      = int(form.get('Daily_Call_Count', 1))
        area_code        = int(form.get('Area_Code', 0))
        number_length    = int(form['Number_Length'])

        features = [
            day_name_code,
            day_of_week,
            hour,
            is_weekend_code,
            call_duration,
            call_cost,
            cost_per_minute,
            dest_code,
            daily_count,
            time_code,
            caller_code,
            pattern_code,
            area_code,
            op_code,
            number_length
        ]

        X = np.array([features])
        prediction = fake_care_model.predict(X)[0]

        return {
            "is_fake": bool(prediction),
            "phone_number": form['Raw_Number'],
            "claimed_brand": form.get('claimed_brand', 'N/A')
        }

    except Exception as e:
        return {
            "is_fake": True,
            "error": str(e),
            "phone_number": form.get('Raw_Number', 'N/A'),
            "claimed_brand": form.get('claimed_brand', 'N/A')
        }
