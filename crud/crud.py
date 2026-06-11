from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import os, logging
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
import paho.mqtt.publish as publish 
import json

logging.basicConfig(format='%(asctime)s - CRUD - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.config["MYSQL_USER"] = os.environ["MYSQL_USER"]
app.config["MYSQL_PASSWORD"] = os.environ["MYSQL_PASSWORD"]
app.config["MYSQL_DB"] = os.environ["MYSQL_DB"]
app.config["MYSQL_HOST"] = os.environ["MYSQL_HOST"]
app.config['PERMANENT_SESSION_LIFETIME']=180
topico = os.environ["TOPICO"] # MAC raspi para enviar comandos 
mqtt_host = os.environ["MQTT_HOST"]
usuario_mqtt = os.environ["MQTT_USR"]
password_mqtt = os.environ["MQTT_PASS"]
mysql = MySQL(app)

# rutas

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    """Registrar usuario"""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("usuario"):
            return "el campo usuario es oblicatorio"

        # Ensure password was submitted
        elif not request.form.get("password"):
            return "el campo contraseña es oblicatorio"

        passhash=generate_password_hash(request.form.get("password"), method='scrypt', salt_length=16)
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO usuarios (usuario, hash) VALUES (%s,%s)", (request.form.get("usuario"), passhash[17:]))
        if mysql.connection.affected_rows():
            flash('Se agregó un usuario')  # usa sesión
            logging.info("se agregó un usuario")
        mysql.connection.commit()
        return redirect(url_for('index'))

    return render_template('registrar.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("usuario"):
            return "el campo usuario es oblicatorio"
        # Ensure password was submitted
        elif not request.form.get("password"):
            return "el campo contraseña es oblicatorio"

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario LIKE %s", (request.form.get("usuario"),))
        rows=cur.fetchone()
        if(rows):
            if (check_password_hash('scrypt:32768:8:1$' + rows[2],request.form.get("password"))):
                session.permanent = True
                session["user_id"]=request.form.get("usuario")
                logging.info("se autenticó correctamente")
                return redirect(url_for('index'))
            else:
                flash('usuario o contraseña incorrecto')
                return redirect(url_for('login'))
    return render_template('login.html')

# Esta seria la pagina principal luego de login
@app.route('/', methods=["GET", "POST"])
@require_login
def index():
    if request.method == "POST":

        topico_seleccionado = request.form.get("topico")
        if not topico_seleccionado:
            flash('Error: Selecciona un nodo de destino')
            return redirect(url_for('index'))

        comando = request.form.get("comando")
        if not comando:
            flash('Error: Selecciona un comando para enviar')
            return redirect(url_for('index'))
            
        credenciales = {'username': usuario_mqtt, 'password': password_mqtt}
        
        if comando == "destello":
            topico_destello = f"{topico_seleccionado}/destello"
            payload = "" 
            publish.single(topico_destello, payload, hostname=mqtt_host, auth=credenciales)
            
            flash('Comando destello enviado con éxito') # Agregado para UX
            logging.info(f"se envió el comando destello al tópico {topico_destello}")

        elif comando == "setpoint":
            valor = request.form.get("valor")
            if not valor:
                flash('Error: Ingresa un valor para el setpoint')
                return redirect(url_for('index'))
            try:
                topico_setpoint = f"{topico_seleccionado}/setpoint"
                valor_float = float(valor)
                payload = f"{valor_float}"
                publish.single(topico_setpoint, payload, hostname=mqtt_host, auth=credenciales)
                
                flash(f'Setpoint actualizado a {valor_float}') # Agregado para UX
                logging.info("se envió el comando setpoint con valor {}".format(valor_float))
            except ValueError:
                flash('Error: Valor inválido para setpoint, ingresa un número')
                return redirect(url_for('index'))
                
    return render_template('index.html', mac_principal=topico)



@app.route("/logout")
@require_login
def logout():
    session.clear()
    logging.info("el usuario {} cerró su sesión".format(session.get("user_id")))
    return redirect(url_for('index'))
