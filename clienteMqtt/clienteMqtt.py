import asyncio, ssl, certifi, logging, os
import aiomqtt

logging.basicConfig(format='%(asctime)s - [%(funcName)s] - %(levelname)s:%(message)s', level=logging.INFO, datefmt='%d/%m/%Y %H:%M:%S %z')

async def atender_topico1(mensaje):
    logging.info(f"Mensaje Recibido en manteca: {mensaje.payload.decode('utf-8')}")

async def atender_topico2(mensaje):
    logging.info(f"Mensaje Recibido en fotosintesis: {mensaje.payload.decode('utf-8')}")

async def escuchar_y_derivar(client, t1, t2):
    async for message in client.messages:
        topico_str = str(message.topic)
        if topico_str == t1:
            asyncio.create_task(atender_topico1(message))
        elif topico_str == t2:
            asyncio.create_task(atender_topico2(message))

async def sumar_contador(estado):
    while True:
        await asyncio.sleep(3)
        estado["contador"] += 1

async def publicar_contador(client, topico, estado):
    while True:
        await asyncio.sleep(5)
        valor = str(estado["contador"])
        await client.publish(topico, payload=valor)
        logging.info(f"\n\n#### Publicando: {valor}")

async def main():
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls_context.verify_mode = ssl.CERT_REQUIRED
    tls_context.check_hostname = True
    tls_context.load_default_certs()
    publicar = os.environ['TOPICO_PUB']
    diccionario = {"contador": 0}

    async with aiomqtt.Client(
        os.environ['SERVIDOR'],
        port=8883,
        tls_context=tls_context,
    ) as client:
        #Suscripcion a topicos
        topicos = os.environ['TOPICO'].split(",")
        for topico in topicos:
            logging.info(f"Suscrito al topico: {topico}")
            await client.subscribe(topico)  

        #Corrutinas
        asyncio.create_task(escuchar_y_derivar(client, topicos[0], topicos[1]))
        asyncio.create_task(sumar_contador(diccionario))
        asyncio.create_task(publicar_contador(client, publicar, diccionario))

        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("OMANO")