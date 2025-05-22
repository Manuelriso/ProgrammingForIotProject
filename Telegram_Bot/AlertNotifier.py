import json
import requests
import asyncio

class TelegramAlertNotifier:
    def __init__(self, application, catalog_url):
        self.application = application
        self.catalog_url = catalog_url

    async def notify_async(self, topic, payload):
        try:
            data = json.loads(payload)

            greenhouse_id = data.get("greenhouse_ID")
            if not greenhouse_id:
                print("Alerta sin greenhouse_ID.")
                return

            # Obtener user_ID desde el catálogo
            url = f"{self.catalog_url}/greenhouses/{greenhouse_id}"
            response = requests.get(url)
            if response.status_code != 200:
                print(f"No se pudo obtener el user_ID de {greenhouse_id}")
                return
            gh_info = response.json()
            user_id = gh_info.get("user_ID")

            if not user_id:
                print(f"Catálogo no devolvió user_ID para {greenhouse_id}")
                return

            # Armar el mensaje de alerta
            area = data.get("area_ID", "desconocida")
            alert_text = data.get("alert", "alerta no especificada")

            message = (
                f"⚠️ ALERT at greenhouse {greenhouse_id}\n"
                f"Area: {area}\n"
                f"Tipo de alerta: {alert_text}"
            )

            await self.application.bot.send_message(chat_id=user_id, text=message)

        except Exception as e:
            print(f"Error en notificación MQTT: {e}")

    def notify(self, topic, payload):
        asyncio.run(self.notify_async(topic, payload))
