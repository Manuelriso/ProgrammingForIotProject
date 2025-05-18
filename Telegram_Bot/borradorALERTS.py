import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Diccionario temporal por usuario
user_data = {}


## Considers that ir receivs something like this:
# alert = { 
#       "greenhouse_id": "GH001",
#   "area_id": "A1",
#   "type": "temperature",  // o "intrusion"
#   "value": 42.0,
#   "timestamp": "2025-05-13T20:20:00Z"
# }

user_data[user_id].setdefault("normal_alerts", [])
user_data[user_id].setdefault("urgent_alerts", [])


## Alerts copy paste chatgpt
import json
from telegram import constants

class AlertNotifier:
    def __init__(self, application, catalog_url, greenhouse_user_map):
        self.application = application  # instancia de telegram.Application
        self.catalog_url = catalog_url
        self.greenhouse_user_map = greenhouse_user_map  # dict {gh_id: user_id}

    async def notify(self, topic, payload):
        try:
            alert = json.loads(payload.decode())
            gh_id = alert["greenhouse_id"]
            alert_type = alert["type"]

            # Paso 1: obtener el user_id
            user_id = self.greenhouse_user_map.get(gh_id)
            if user_id is None:
                # Intentar consultarlo al catálogo
                user_id = await self.get_user_id_from_catalog(gh_id)
                if user_id is None:
                    print(f"[WARN] No se pudo asociar GH {gh_id} a ningún usuario.")
                    return
                self.greenhouse_user_map[gh_id] = user_id  # cachearlo

            # Paso 2: almacenar o enviar según prioridad
            if alert_type == "intrusion":
                # urgente: se envía inmediatamente sin cambiar el estado
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=f"🚨 *¡INTRUSIÓN DETECTADA!*\nGreenhouse: {gh_id}\nÁrea: {alert['area_id']}\nHora: {alert['timestamp']}",
                    parse_mode=constants.ParseMode.MARKDOWN
                )
            else:
                # normal: se guarda para mostrar más tarde
                user_data.setdefault(user_id, {}).setdefault("normal_alerts", []).append(alert)

        except Exception as e:
            print(f"[ERROR] Alerta MQTT malformada o error al procesar: {e}")

    async def get_user_id_from_catalog(self, greenhouse_id):
        import requests
        try:
            response = requests.get(f"{self.catalog_url}/greenhouses/{greenhouse_id}")
            if response.status_code == 200:
                return response.json().get("user_ID")
        except Exception as e:
            print(f"[ERROR] Al consultar catálogo: {e}")
        return None




class AlertNotifier:
    def __init__(self, application, catalog_url, user_map):
        self.application = application
        self.catalog_url = catalog_url
        self.greenhouse_user_map = user_map  # referencia al mismo diccionario

    async def notify(self, topic, payload):
        try:
            alert = json.loads(payload.decode())
            gh_id = alert["greenhouse_id"]
            alert_type = alert["type"]

            # Paso 1: usar o actualizar el user_id desde el mapa
            user_id = self.greenhouse_user_map.get(gh_id)
            if not user_id:
                user_id = await self.get_user_id_from_catalog(gh_id)
                if not user_id:
                    print(f"[WARN] No se pudo asociar GH {gh_id} a ningún usuario.")
                    return
                self.greenhouse_user_map[gh_id] = user_id

            # Paso 2: mostrar alerta (igual que antes)
            ...

        except Exception as e:
            print(f"[ERROR] {e}")
