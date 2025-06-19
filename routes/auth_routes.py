import MySQLdb
from flask import Blueprint, request, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import mysql
from flask import redirect, flash
from flask_mail import Mail,Message
import random, time

auth_bp = Blueprint('auth',__name__)
mail = Mail()


@auth_bp.route('/signup')
def signup():
    return render_template('signup.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        #otp
        otp = str(random.randint(100000,999999))
        now = int(time.time())

        session['temp_user'] = {'name':name, 'email':email,'password':password}
        session['otp'] = otp
        session['otp_time']=now

        msg = Message(subject="OTP Verification", sender="dheerajroot01@gmail.com", recipients=[email])
        msg.body = f"Your OTP is {otp}. It will expire in 5 minutes."
        mail.send(msg)

        flash('OTP sent to your email. Please verify.','info')
        return redirect('/verify-otp')


        
    
    # In case someone visits /register via GET, show the signup form
    return render_template('signup.html')

@auth_bp.route('/verify-otp', methods=['GET','POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        correct_otp = session.get('otp')
        otp_time = session.get('otp_time')
        user_data = session.get('temp_user')

        if not otp_time or time.time()-otp_time>300:
            flash('OTP expired. Please resend.','warning')
            return redirect('/verify-otp')
        if entered_otp ==  correct_otp and user_data:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO users (name, email, password, email_verified) VALUES (%s, %s, %s, %s)",
                        (user_data['name'], user_data['email'], user_data['password'], True))
            mysql.connection.commit()
            cur.close()


            session['email'] = user_data['email']
            session.pop('otp',None)
            session.pop('otp_time',None)
            session.pop('temp_user',None)

            flash('Email verified and account created.', 'success')
            return redirect('/login')
        else:
            flash('Invalid OTP. Try again.','danger')
    return render_template('verify_otp.html')


@auth_bp.route('/resend-otp')
def resend_otp():
    user_data = session.get('temp_user')
    if not user_data:
        return redirect('/register')
    
    otp = str(random.randint(100000,999999))
    session['otp'] = otp
    session['otp_time'] = int(time.time())

    msg = Message(subject="Resent OTP Code", sender="dheerajroot01@gmail.com", recipients=[user_data['email']])
    msg.body = f"Your new OTP is {otp}. It will expire in 5 minutes."
    mail.send(msg)

    flash('OTP resent successfully.','info')
    return redirect('/verify-otp')









@auth_bp.route('/user-details',methods=['GET','POST'])
def user_details():
    if request.method == 'POST':
        email = session.get('email')
        cur = mysql.connection.cursor()
        # find the user ID
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        user_id = user['id']

        phone = request.form['phone']
        session['phone']=phone

        # grab all form fields
        phone  =  request.form['phone']
        home_lat = float(request.form['home_lat'])
        home_lon = float(request.form['home_lon'])
        known_devices = request.form['known_devices'] #commap-sep string
        device_id = request.form['device_id']
        txn_lat = float(request.form['txn_lat'])
        txn_lon = float(request.form['txn_lon'])
        amount = float(request.form['amount'])
        failed_attempts = int(request.form['failed_attempts'])

        # upse
        upsert_sql = """
          INSERT INTO profile_form (
            user_id, phone, home_lat, home_lon, known_devices,
            device_id, txn_lat, txn_lon, amount, failed_attempts
          ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
          )
          ON DUPLICATE KEY UPDATE
            phone           = VALUES(phone),
            home_lat        = VALUES(home_lat),
            home_lon        = VALUES(home_lon),
            known_devices   = VALUES(known_devices),
            device_id       = VALUES(device_id),
            txn_lat         = VALUES(txn_lat),
            txn_lon         = VALUES(txn_lon),
            amount          = VALUES(amount),
            failed_attempts = VALUES(failed_attempts)
        """


        cur.execute(upsert_sql, [
            user_id, phone, home_lat, home_lon, known_devices,
            device_id, txn_lat, txn_lon, amount, failed_attempts
        ])


        mysql.connection.commit()
        cur.close()



        return redirect('/dashboard')
    

    if request.method =='GET':
        email = session.get('email')
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('SELECT id FROM users WHERE email=%s',(email,))
        user = cur.fetchone()

        if not user:
            flash('User not found',"danger")
            return redirect('/login')
        
        user_id = user['id']

        # Fetch profile_form data if exists
        cur.execute("SELECT * FROM profile_form WHERE user_id=%s",(user_id,))
        data = cur.fetchone()
        cur.close()

        return render_template('user_details.html', form_data=data)


    return render_template('user_details.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        


        if user and not user['email_verified']:
            flash('Please verify your email before logging in.','warning')
            return redirect('/login')



        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['username'] = user['name']  # Optional


            #fetch phone numeber from profile_form
            cur.execute("SELECT phone FROM profile_form WHERE user_id=%s",(user['id'],))
            profile = cur.fetchone()
            if profile and profile['phone']:
                session['phone'] = profile['phone']

            cur.close()




            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid credentials. Please try again.', 'danger')
            return redirect('/login')

    return render_template('login.html')

