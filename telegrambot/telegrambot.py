from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import logging, os, asyncio, aiomysql, traceback, locale
# import matplotlib.pyplot as plt
from io import BytesIO
import aiomqtt

token=os.environ["TB_TOKEN"]
mqtt_host = os.environ["MQTT_HOST"]
usuario_mqtt = os.environ["MQTT_USR"]
password_mqtt = os.environ["MQTT_PASS"]
topico = os.environ["TOPICO"]


logging.basicConfig(format='%(asctime)s - TelegramBot - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("se conectó: " + str(update.message.from_user.id))
    if update.message.from_user.first_name:
        nombre=update.message.from_user.first_name
    else:
        nombre=""
    if update.message.from_user.last_name:
        apellido=update.message.from_user.last_name
    else:
        apellido=""
    kb = [["temperatura"],["humedad"],["gráfico temperatura"],["gráfico humedad"]]
    await context.bot.send_message(update.message.chat.id, text="Bienvenido al Bot "+ nombre + " " + apellido,reply_markup=ReplyKeyboardMarkup(kb))

async def publish_mqtt(topic: str, payload: str):
    logging.info(f"Intentando publicar en {topic}: {payload}") # Log de inicio
    try:
        # IMPORTANTE: Definí explícitamente el puerto por si acaso
        async with aiomqtt.Client(hostname=mqtt_host, port=1883, username=usuario_mqtt, password=password_mqtt) as client:
            await client.publish(topic, payload)
            logging.info(f"ÉXITO: Mensaje entregado a Mosquitto") # Log de éxito
    except Exception as error:  # Atrapa TODOS los errores posibles
        logging.error(f"ERROR CRÍTICO MQTT: {error}")

async def cmd_destello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Destello no requiere valor, mandamos un "1" por convención (la Raspi lo ignora)
    await publish_mqtt(f"{topico}/destello", "1")
    await update.message.reply_text("Comando enviado: destello")

async def cmd_rele(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comando, valor = update.message.text.lower().split()
    await publish_mqtt(f"{topico}/{comando}", valor)
    await update.message.reply_text(f"Comando enviado: {comando} -> {valor}")

async def cmd_modo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comando, valor = update.message.text.lower().split()
    await publish_mqtt(f"{topico}/{comando}", valor)
    await update.message.reply_text(f"Comando enviado: {comando} -> {valor}")

async def cmd_periodo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comando, valor = update.message.text.lower().split()
    await publish_mqtt(f"{topico}/{comando}", valor)
    await update.message.reply_text(f"Comando enviado: {comando} -> {valor}")

async def cmd_setpoint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comando, valor = update.message.text.lower().split()
    await publish_mqtt(f"{topico}/{comando}", valor)
    await update.message.reply_text(f"Comando enviado: {comando} -> {valor}")

def main():
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.Regex(r"(?i)^destello$"), cmd_destello))
    application.add_handler(MessageHandler(filters.Regex(r"(?i)^rele (0|1)$"), cmd_rele))
    application.add_handler(MessageHandler(filters.Regex(r"(?i)^modo (auto|manual)$"), cmd_modo))
    application.add_handler(MessageHandler(filters.Regex(r"(?i)^periodo [1-9][0-9]*$"), cmd_periodo))
    application.add_handler(MessageHandler(filters.Regex(r"(?i)^setpoint \d+(\.\d+)?$"), cmd_setpoint))
    application.run_polling()

if __name__ == '__main__':
    main()
