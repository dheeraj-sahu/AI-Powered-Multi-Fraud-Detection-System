from flask_mysqldb import MySQL

mysql = MySQL()

def init_mysql(app):
    app.config['MYSQL_HOST'] = 'localhost'  # e.g., 'aws.connect.psdb.io'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'D9943sahu?+#'
    app.config['MYSQL_DB'] = 'fraud'
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    mysql.init_app(app)

