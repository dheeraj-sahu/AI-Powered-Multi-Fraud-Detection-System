from flask import Flask , render_template, redirect
from flask_cors import CORS
from routes.auth_routes import auth_bp
from routes.transaction_routes import tx_bp
from database import init_mysql, mysql
from flask import session
from routes.detection_routes import detection_bp
from flask_mail import Mail


app =Flask(__name__)
app.secret_key = 'cipherstorm-secret-123'
CORS(app)
init_mysql(app)


#Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'dheerajroot01@gmail.com'
app.config['MAIL_PASSWORD'] = 'bxbn myke qzhs yqre'
mail = Mail(app)



app.register_blueprint(auth_bp)
app.register_blueprint(tx_bp)
app.register_blueprint(detection_bp)



@app.route('/')
def home():
    return render_template('index.html')


@app.context_processor
def inject_user():
    return {
        'logged_in': bool(session.get('user_id')),
        'username': session.get('username'),
    }



@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__=='__main__':
    app.run(debug=True)