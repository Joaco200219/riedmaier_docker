from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
import logging, os, asyncio, aiomysql, traceback, locale
from io import BytesIO
import aiomqtt
import json

token = os.environ["TB_TOKEN"]
mqtt_host = os.environ["MQTT_HOST"]
usuario_mqtt = os.environ["MQTT_USR"]
password_mqtt = os.environ["MQTT_PASS"]
topico = os.environ["TOPICO"]
ultimo_estado = {"datos": "Aún no se han recibido datos de la Raspberry."} #Mensajes de estado

logging.basicConfig(format='%(asctime)s - TelegramBot - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Definimos los estados de la conversación
CMD, VALUE = range(2)

async def publish_mqtt(topic: str, payload: str):
    logging.info(f"Intentando publicar en {topic}: {payload}")
    try:
        async with aiomqtt.Client(hostname=mqtt_host, port=1883, username=usuario_mqtt, password=password_mqtt) as client:
            await client.publish(topic, payload)
            logging.info("ÉXITO: Mensaje entregado a Mosquitto")
    except Exception as error:
        logging.error(f"ERROR CRÍTICO MQTT: {error}")

async def mqtt_listener(application: Application): #Para escuchar el tópico de la Raspi y actualizar el estado global
    """Escucha permanentemente el tópico de la Raspi y actualiza la variable global."""
    while True:
        try:
            async with aiomqtt.Client(hostname=mqtt_host, port=1883, username=usuario_mqtt, password=password_mqtt) as client:
                # Nos suscribimos al tópico exacto donde publica la Raspi
                await client.subscribe(f"{topico}/")
                logging.info(f"Escuchando estado en {topico}/...")
                
                async for message in client.messages:
                    payload = message.payload.decode()
                    # Actualizamos la variable global con el nuevo diccionario
                    ultimo_estado["datos"] = json.loads(payload)
        except Exception as error:
            logging.error(f"Error en listener MQTT: {error}. Reintentando en 5s...")
            await asyncio.sleep(5)

async def post_init(application: Application):
    """Esta función la llama Telegram automáticamente al arrancar."""
    asyncio.create_task(mqtt_listener(application))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("se conectó: " + str(update.message.from_user.id))
    nombre = update.message.from_user.first_name if update.message.from_user.first_name else ""
    apellido = update.message.from_user.last_name if update.message.from_user.last_name else ""
    
    # Teclado consolidado con las mediciones y los nuevos comandos de control
    kb = [
        ["estado"], # Botón para mostrar el estado actual
        ["rele", "modo"],
        ["setpoint", "periodo", "destello"]
    ]
    
    await context.bot.send_message(
        update.message.chat.id, 
        text=f"Bienvenido al Bot {nombre} {apellido}. Seleccione una acción:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True) # resize_keyboard ajusta el tamaño de los botones
    )
    
    # Indicamos que pasamos al estado de esperar un comando (CMD)
    return CMD

async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos = ultimo_estado["datos"]
    
    if isinstance(datos, str):
        # Si sigue siendo el string inicial (no llegaron datos)
        await update.message.reply_text(datos)
        return CMD
    
    # Formateamos los datos si ya tenemos el diccionario JSON
    texto_estado = (
        f"📊 *Estado Actual*\n\n"
        f"🌡️ Temperatura: {datos.get('temp')} ºC\n"
        f"💧 Humedad: {datos.get('hum')} %\n"
        f"⚙️ Modo: {datos.get('modo').upper()}\n"
        f"🎯 Setpoint: {datos.get('setpoint')} ºC\n"
        f"⏱️ Período: {datos.get('periodo')} s"
    )
    
    await update.message.reply_text(texto_estado, parse_mode='Markdown')
    return CMD

async def cmd_destello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Destello se ejecuta directo y vuelve al estado CMD para seguir esperando botones
    await publish_mqtt(f"{topico}/destello", "1")
    await update.message.reply_text("Comando enviado: destello")
    return CMD

async def ask_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atrapa el botón presionado, guarda el contexto y pide el valor."""
    comando = update.message.text.lower()
    context.user_data["comando"] = comando # Guardamos qué botón se apretó en la memoria del usuario
    
    mensajes_ayuda = {
        "rele": "Ingrese el valor para el relé (0 o 1):",
        "modo": "Ingrese el modo (auto o manual):",
        "periodo": "Ingrese el periodo en segundos (ej. 60):",
        "setpoint": "Ingrese el setpoint numérico (ej. 25.5):"
    }
    
    await update.message.reply_text(mensajes_ayuda.get(comando, "Ingrese el valor:"))
    
    # Avanzamos al estado de esperar el valor escrito
    return VALUE

async def receive_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el texto escrito por el usuario, lo valida y lo publica en MQTT."""
    valor = update.message.text.lower()
    comando = context.user_data.get("comando") # Recuperamos qué botón había apretado
    
    if not comando:
        # Por seguridad, si se pierde el contexto
        await update.message.reply_text("Error de contexto. Por favor, vuelva a seleccionar una acción.")
        return CMD

    # --- BLOQUE DE VALIDACIÓN ---
    es_valido = False
    error_msg = ""

    if comando == "rele":
        if valor in ["0", "1"]:
            es_valido = True
        else:
            error_msg = "Error: El relé solo acepta '0' o '1'. Ingrese el valor nuevamente:"
            
    elif comando == "modo":
        if valor in ["auto", "manual"]:
            es_valido = True
        else:
            error_msg = "Error: El modo debe ser 'auto' o 'manual'. Ingrese el valor nuevamente:"
            
    elif comando == "periodo":
        if valor.isdigit() and int(valor) > 0:
            es_valido = True
        else:
            error_msg = "Error: El periodo debe ser un número entero positivo (ej. 60). Ingrese nuevamente:"
            
    elif comando == "setpoint":
        try:
            float(valor) # Intentamos convertir a decimal
            es_valido = True
        except ValueError:
            error_msg = "Error: El setpoint debe ser un número válido (ej. 25 o 25.5). Ingrese nuevamente:"

    # --- EJECUCIÓN ---
    if es_valido:
        await publish_mqtt(f"{topico}/{comando}", valor)
        await update.message.reply_text(f"Comando enviado: {comando} -> {valor}")
        return CMD # Todo ok, volvemos al menú principal
    else:
        await update.message.reply_text(error_msg)
        return VALUE # Dato inválido, nos quedamos esperando que escriba bien

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite salir del flujo de conversación."""
    await update.message.reply_text("Operación cancelada. Use /start para volver al menú principal.")
    return ConversationHandler.END

def main():
    # Enganchamos el post_init para que arranque el listener al iniciar el bot
    application = Application.builder().token(token).post_init(post_init).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CMD: [
                # Agregamos el handler para el nuevo botón "estado"
                MessageHandler(filters.Regex(r"(?i)^estado$"), cmd_estado),
                
                MessageHandler(filters.Regex(r"(?i)^destello$"), cmd_destello),
                MessageHandler(filters.Regex(r"(?i)^(rele|modo|setpoint|periodo)$"), ask_value),
            ],
            VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_value)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)]
    )
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()