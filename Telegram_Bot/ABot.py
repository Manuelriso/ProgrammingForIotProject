# ABot.py
import json
import re
import requests
from requests.exceptions import RequestException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from datetime import datetime
import time
from functools import partial
import asyncio
import MyMQTTforBOT
from AlertNotifier import AlertNotifier
from sharedUtils import *

######################### CONVERSATION STATES #########################
# Conversation states
MAIN_MENU, WAIT_NEW_GH_ID, WAIT_PLANT, CHECK_FIRST_THRESHOLD, SET_THRESHOLDS, INPUT_GH_ID, HANDLING_GH_ID, CONFIRM_X_GH, MANAGE_GH, SHOWING_AVAILABLE_AREAS, CONFIRM_X_A, CONFIRM_X_BOTH, ADD_A, WAIT_AREA_INSTRUCTION, WAIT_ACTUATOR_STATE, FINAL_STAGE = range(16)
######################### CONFIGURATION #########################
def load_config():
    with open('configBot.json') as config_file:
        config = json.load(config_file)
    return config
######################### Keyboards #########################
## Main menu keyboard
main_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("➕ Add Greenhouse", callback_data='add_greenhouse')],
    [InlineKeyboardButton("🛠️ Manage Greenhouses", callback_data='manage_greenhouses')],
    [InlineKeyboardButton("🗑️ Delete Greenhouse", callback_data='delete_greenhouse')],
    [InlineKeyboardButton("👋 Exit", callback_data='bye')]
])
## Back to main menu keyboard
back_to_MM = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data='back_to_main_menu')]])
## Exit button
bye_button = InlineKeyboardMarkup([[InlineKeyboardButton("👋 Exit", callback_data='bye')]])
## Combined back to main menu and exit button
end_markup = InlineKeyboardMarkup([back_to_MM.inline_keyboard[0] + bye_button.inline_keyboard[0]])

A_Mg_markup = InlineKeyboardMarkup([
    # Sensors (3 in a row)
    [InlineKeyboardButton("🌫️ Humidity", callback_data='check_humidity'),
     InlineKeyboardButton("🌡️ Temperature", callback_data='check_temperature'),
     InlineKeyboardButton("☀️ Luminosity", callback_data='check_luminosity')],
    # Actuators (3 in a row)
    [InlineKeyboardButton("💧 Pump", callback_data='manage_pump'),
     InlineKeyboardButton("🌬️ Fan", callback_data='manage_fan'),
     InlineKeyboardButton("💡 Light", callback_data='manage_light')],
    # General options (2 in a row)
    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='back_to_main_menu'),
     InlineKeyboardButton("👋 Exit", callback_data='bye')]
])

areas_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("🛠️ Manage Areas", callback_data='gestion_areas'),
    InlineKeyboardButton("➕ Add Area", callback_data='agregar_areas')],
    [InlineKeyboardButton("📊 Historical Data", callback_data='storical_data_gh'),
     InlineKeyboardButton("🗑️ Delete Area", callback_data='eliminacion_area')],
    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='back_to_main_menu')]
])

######################### AUXILIARY FUNCTIONS #########################
### Verify if the greenhouse ID exists in the database
async def check_gh_id_exists(catalog_url, greenhouse_id) -> bool:
    try:
        response = requests.get(f"{catalog_url}greenhouses", timeout=5)
        if response.status_code == 200:
            greenhouses = response.json().get("greenhouses", [])
            result = any(int(gh['greenhouseID']) == int(greenhouse_id) for gh in greenhouses)
            return result
        else:
            print("Response status not 200:", response.status_code)
        return False
    except requests.exceptions.RequestException as e:
        print("Request exception:", e)
        return True

### Create a new greenhouse in the database with first area
async def create_greenhouse_and_area(catalog_url, user_id, greenhouse_id, plant_type,temperature_threshold, humidity_threshold, light_threshold) -> bool:
    try:
        new_greenhouse = {
            "greenhouseID": int(greenhouse_id),
            "telegram_ID": user_id,
            "numberOfAreas": 1,
            "creation_date": datetime.now().strftime("%d-%m-%Y"),
            "areas": [
            {
                "ID": 1, 
                "humidityThreshold": humidity_threshold,  
                "temperatureThreshold": temperature_threshold,
                "luminosityThreshold": light_threshold,
                "plants": plant_type,
                "temperatureDataTopic": f"greenhouse{int(greenhouse_id)}/area1/temperature",
                "humidityDataTopic": f"greenhouse{int(greenhouse_id)}/area1/humidity",
                "luminosityDataTopic": f"greenhouse{int(greenhouse_id)}/area1/luminosity",
                "motionTopic": f"greenhouse{int(greenhouse_id)}/area1/motion",
                "motionDetected": 0,
                "currentTemperature": "Unknown",
                "currentHumidity": "Unknown",
                "currentLuminosity": "Unknown",
                "pumpActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/pump",
                "lightActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/light",
                "ventilationActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/ventilation",
                "pump": 0,
                "light": "off",
                "ventilation": 0
                
            }
            ]
        }
        response = requests.post(f"{catalog_url}greenhouse", json=new_greenhouse)
        if response.status_code == 201:
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False

### Create a new area in the database
async def create_area(catalog_url, greenhouse_id, area_id, plant_type, temperature_threshold, humidity_threshold, light_threshold) -> bool:
    try:
        new_area = {
            "ID": area_id,
            "humidityThreshold": humidity_threshold,
            "temperatureThreshold": temperature_threshold,
            "luminosityThreshold": light_threshold, 
            "plants": plant_type,
            "temperatureDataTopic": f"greenhouse{int(greenhouse_id)}/area{area_id}/temperature",
            "humidityDataTopic": f"greenhouse{int(greenhouse_id)}/area{area_id}/humidity",
            "luminosityDataTopic": f"greenhouse{int(greenhouse_id)}/area{area_id}/luminosity",
            "motionTopic": f"greenhouse{int(greenhouse_id)}/area{area_id}/motion",
            "motionDetected": 0,
            "currentTemperature": "Unknown",
            "currentHumidity": "Unknown",
            "currentLuminosity": "Unknown",
            "pumpActuation": f"greenhouse{int(greenhouse_id)}/area{area_id}/actuation/pump",
            "lightActuation": f"greenhouse{int(greenhouse_id)}/area{area_id}/actuation/light",
            "ventilationActuation": f"greenhouse{int(greenhouse_id)}/area{area_id}/actuation/ventilation",
            "pump": 0,
            "light": "off",
            "ventilation": 0
        }
        response = requests.post(f"{catalog_url}greenhouse{greenhouse_id}/area", json=new_area) #####POST
        if response.status_code == 201:
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False

### Check the next area ID to be used while creating a new area
## Always use the next available ID from 1 to 4
async def next_area_id(catalog_url, greenhouse_id) -> int:
    try:
        response = requests.get(f"{catalog_url}greenhouses/{greenhouse_id}")
        if response.status_code == 200:
            areas = response.json().get("areas", [])
            area_ids = [area['ID'] for area in areas]
            # If there are already 4 areas, no more can be added
            if len(area_ids) >= 4:
                return 0
            # Find the first available ID from 1 to 4
            for i in range(1, 5):
                if i not in area_ids:
                    return i  # Return the first available ID
            return None  # Just in case
        else:
            return None
    except requests.exceptions.RequestException:
        return None

### Delete an entire greenhouse
async def delete_entire_greenhouse(catalog_url, greenhouse_id) -> bool:
    try:
        response = requests.delete(f"{catalog_url}greenhouse/{greenhouse_id}")
        print(f"Response content: {response.text}")
        if response.status_code == 204:
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False
    
### Delete an area inside a greenhouse  
async def delete_area(catalog_url, greenhouse_id, area_id) -> bool:
    try:
        response = requests.delete(f"{catalog_url}greenhouse{greenhouse_id}/area/{area_id}")
        if response.status_code == 204:
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False

### List all the areas in a greenhouse
async def list_areas(catalog_url, greenhouse_id) -> list:
        try:
            response = requests.get(f"{catalog_url}greenhouse{greenhouse_id}/areas")
            if response.status_code == 200:
                data = response.json()
                areas = data.get("areas", [])  # Ensure 'areas' exists and is a list
                if not areas:
                    print(f"Warning: The greenhouse {greenhouse_id} has no associated areas.")
                    return []
                area_list = [(area['ID'], area['plants']) for area in areas]
                return area_list
            else:
                print(f"Error in the request: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return []

### Get the details of a specific area in a greenhouse       
async def get_area(catalog_url, greenhouse_id, areaID) -> list:
    try: #greenhouse1/areas/1 
        response = requests.get(f"{catalog_url}greenhouse{greenhouse_id}/areas/{areaID}")
        if response.status_code == 200:
            area = response.json()
            return area
        else:
            print(f"Error in the request: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error while retrieving area details: {e}. Contact support.")
        return None

### Get the user id from a greenhouse id
async def get_user_id_from_gh_id(catalog_url, greenhouse_id) -> int:
    try:
        response = requests.get(f"{catalog_url}greenhouses/{greenhouse_id}")
        if response.status_code == 200:
            greenhouse = response.json()
            return greenhouse.get("telegram_ID")
        return None
    except requests.exceptions.RequestException:
        return None

### Build a suggestion keyboard with a suggested value for stablishing thresholds
async def build_suggestion_keyboard(suggested_value: int, include_back: bool = True) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(f"Suggested: {suggested_value}", callback_data=str(suggested_value))]]
    if include_back:
        keyboard.append([InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]) #Keep like this
    return InlineKeyboardMarkup(keyboard)

### Helper function to escape Markdown v2 special characters
def escape_md_v2(text: str) -> str:
    return re.sub(r'([_*\[\]()~`>#+=|{}.!\\-])', r'\\\1', str(text))


############################### CONVERSATION FUNCTIONS ###############################    
async def handle_storical_data_gh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    show_text = (
        "📡 Follow the next link to see the data of the greenhouse that *your plan has access* to:\n"
        "⚠️ _For more functionalities please upgrade your plan\\._ \n\n"
        "🌡️ Temperatures: [View Data](https://thingspeak.mathworks.com/channels/2907689)\n"
        "💧 Humidity: [View Data](https://thingspeak.mathworks.com/channels/2907692)\n"
        "💡 Luminosity: [View Data](https://thingspeak.mathworks.com/channels/2907694)"
    )
    await update.callback_query.message.reply_text(
        show_text,
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
        reply_markup=end_markup
    )
    #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
    return FINAL_STAGE

### Retrieve the actuator state for a specific area in a greenhouse
async def check_actuator_state(catalog_url, greenhouse_id, area_processing, actuator_type):
    try:
        area = await get_area(catalog_url, greenhouse_id, area_processing)
        if area is None:
            print("❌ Area not found")
            return None
        if actuator_type == "manage_pump":
            state = area.get('pump')
        elif actuator_type == "manage_light":
            state = area.get('light')
        elif actuator_type == "manage_fan":
            state = area.get('ventilation')
        else:
            print("Invalid actuator_type:", actuator_type)
            return None
        return state
    except Exception as e:
        print(f"❌ Error while retrieving the actuator state: {e}")
        return None

############################# ALERTS FUNCTIONS #############################
### Format the alert message to be sent to the user
def format_alert_message(alert_dict, already_tried):
    GH_ID, AREA_ID = get_ids(alert_dict.get('bn', ''))
    event = alert_dict.get('e', [{}])[0]  
    alerttype = event.get('n', 'unknown')
    timestamp = event.get('t', None)
    
    # Convert timestamp to readable date if it exists
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        timestamp_str = dt.strftime('%d-%m-%Y %H:%M:%S')
    else:
        timestamp_str = timestamp
    
    msg = (
        f"🚨 *Alert detected!*\n\n"
        f"🏡 *Greenhouse:* {GH_ID}\n"
        f"📍 *Area:* {AREA_ID}\n"
        f"🔔 *Alert type:* {alerttype.capitalize()}\n"
        f"🕒 *Date and time:* {timestamp_str}\n"
    )
    if already_tried:
        msg += "\n⚠️ There was a missed alert. Please contact support."
    return msg

############################# 🌟 BOT MAIN CLASS WITH METHODS 🌟 #############################
############################# 🚀 BOT MAIN CLASS WITH METHODS 🚀 #############################
############################# 🌱 BOT MAIN CLASS WITH METHODS 🌱 #############################
############################# 🌈 BOT MAIN CLASS WITH METHODS 🌈 #############################
############################# 💡 BOT MAIN CLASS WITH METHODS 💡 #############################
############################# 🎉 BOT MAIN CLASS WITH METHODS 🎉 #############################
class BotMain:
    def __init__(self, config):
        self.token = config['telegram_token']
        self.catalog_url = config['catalog_url']
        self.default_thresholds = config['default_thresholds']
        self.mqtt_broker = config['brokerIP']
        self.broker_port = config['port']
        self.serviceInfo = config['serviceInfo']
        self.actualTime = time.time()

        # Telegram application setup
        self.application = Application.builder().token(self.token).build()
        self.application.bot_data['catalog_url'] = self.catalog_url
        self.application.bot_data['default_thresholds'] = self.default_thresholds

        ### Initialization of variables and dictionaries
        # Temporary dictionary per user and session to manage chat processes
        self.user_data = {}
        # Alert queue
        self.alert_queue = asyncio.Queue(maxsize=100)
        self.queue_lock = asyncio.Lock()
        # Dictionary to regulate alert sending moments
        self.user_states = {}
        # Map to store values and link them with the correct users, handled by the AlertNotifier (and the bot)
        self.greenhouse_user_map = {}
        self.greenhouse_map_lock = asyncio.Lock()
        # Dictionaries and vairable for pending alerts, to process them
        self.pending_alerts = {}
        self.already_retried = {}  # To track if an alert has already been retried
        self.alert_data = None 

        # Initialize greenhouse_user_map
        self.initialize_greenhouse_user_map()

        # Setup MQTT + Notifier 
        self.mqtt_client, self.alert_notifier = self.setup_mqtt_and_notifier()
  
        # Add ConversationHandler
        self.application.add_handler(self._build_conversation_handler())
        # Register the service in the catalog
        self.registerService()


    def registerService(self):
        self.serviceInfo['last_update'] = self.actualTime
        requests.post(f'{self.catalog_url}service', data=json.dumps(self.serviceInfo))
    
    async def update_registration_service(self):
        """Periodically updates the bot's registration in the catalog service."""
        while True:
            try:
                await asyncio.sleep(30)
                self.serviceInfo['last_update'] = time.time()
                requests.put(f'{self.catalog_url}service', data=json.dumps(self.serviceInfo))
                await asyncio.sleep(30)  # Update every 60 seconds
            except Exception as e:
                print(f"[ERROR] Failed to update registration: {e}")

    def setup_mqtt_and_notifier(self):
        try:
            # Instantiate the MQTT client
            self.mqtt_client = MyMQTTforBOT.MyMQTT("TelBotMQTTClient", self.mqtt_broker, self.broker_port)
            # Instantiate the AlertNotifier with the MQTT client and catalog URL
            self.alert_notifier = AlertNotifier(
                mqtt_client=self.mqtt_client,
                catalog_url=self.catalog_url)
            # Assign the enqueue method to the notifier
            self.alert_notifier.enqueue_method = self.enqueue_alert_message
            print(" The enqueue method has been set in the notifier.. Proof: ", self.alert_notifier.enqueue_method)
            # Set the notifier for the MQTT client
            self.mqtt_client.notifier = self.alert_notifier
            self.mqtt_client.start()
            return self.mqtt_client, self.alert_notifier
        except Exception as e:
            print(f"Error setting up MQTT and AlertNotifier: {e}")
            return None, None

    ## Enqueue alert messages to the alert queue    
    def enqueue_alert_message(self, message: dict):
        try:
            # print("The try with lock")
            # async with self.queue_lock:
            print("inside the try awasit put en la cola.")
            self.alert_queue.put_nowait(message)
            print('Encolada che la alerta:', message)
            # asyncio.create_task(self.alert_queue.put(message))
            # self.alert_queue.put_nowait(message)
        except asyncio.QueueFull:
            print("Alert queue is full. Dropping message:", message)
        except Exception as e:
            print(f"Error enqueuing alert message: {e}")

    ## Initialize the greenhouse_user_map from the data from the catalog
    def initialize_greenhouse_user_map(self):
            try:
                response = requests.get(f"{self.catalog_url}greenhouses", timeout=10)
                all_greenhouses = response.json().get("greenhouses", [])
                for greenhouse in all_greenhouses:
                    gh_id = int(greenhouse.get("greenhouseID"))
                    user = greenhouse.get("telegram_ID")
                    if gh_id and user:
                        self.greenhouse_user_map[gh_id] = {"user": user, "areas": {}}
                        for area in greenhouse.get("areas", []):
                            area_id = int(area.get("ID"))
                            if area_id:
                                self.greenhouse_user_map[gh_id]["areas"][area_id] = {"LastMotionValue": 0, "timestampMotion": None}
                print("Greenhouse user map initialized successfully.")
            except (RequestException, ValueError) as e:
                print(f"Error initializing greenhouse_user_map: {e}")

    ## Build the conversation handler for the bot with all the states and transitions
    def _build_conversation_handler(self):
        return ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, self.start)],
            states={
                MAIN_MENU: [
                    CallbackQueryHandler(self.handle_bye, pattern='^bye$'),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='^back_to_main_menu$'),
                    CallbackQueryHandler(self.handle_wait_new_gh_id , pattern='^add_greenhouse$'),
                    CallbackQueryHandler(self.handle_input_gh_id, pattern='^manage_greenhouses$'),
                    CallbackQueryHandler(self.handle_input_gh_id, pattern='^delete_greenhouse$'),
                ],
                WAIT_NEW_GH_ID: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_check_gh_id_and_wait_new_gh_plant),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                WAIT_PLANT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_plant_set_start_thresholds),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CHECK_FIRST_THRESHOLD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,self.handle_threshold_input ),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                SET_THRESHOLDS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_threshold_input),
                    CallbackQueryHandler(self.handle_threshold_input, pattern=r"^\d+$"),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                INPUT_GH_ID: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_input_gh_id),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                HANDLING_GH_ID: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_gh_id_selection),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CONFIRM_X_GH: [
                    CallbackQueryHandler(self.handle_delete_gh, pattern='confirm_delete_gh'),
                    CallbackQueryHandler(self.handle_delete_gh, pattern='cancel_delete_gh'),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                MANAGE_GH: [
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                    CallbackQueryHandler(self.handle_add_area, pattern='agregar_areas'),
                    CallbackQueryHandler(self.handle_manage_gh), #Rest of the options
                ],
                SHOWING_AVAILABLE_AREAS: [
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'), #first checks if this happened
                    CallbackQueryHandler(self.checking_what_to_do_showed_areas),
                ],                 
                ADD_A : [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_wait_new_a_plant),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CONFIRM_X_A: [
                    CallbackQueryHandler(self.handle_delete_area, pattern='confirm_delete_area'),
                    CallbackQueryHandler(self.handle_delete_area, pattern='cancel_delete_area'),
                ],        
                WAIT_AREA_INSTRUCTION
                : [
                    # CallbackQueryHandler(handle_acciones, pattern='acciones_invernadero'),
                    CallbackQueryHandler(self.handle_verify, pattern='check_humidity'),
                    CallbackQueryHandler(self.handle_verify, pattern='check_temperature'),
                    CallbackQueryHandler(self.handle_verify, pattern='check_luminosity'),
                    CallbackQueryHandler(self.handle_actuators_a, pattern='manage_pump'),
                    CallbackQueryHandler(self.handle_actuators_a, pattern='manage_fan'),
                    CallbackQueryHandler(self.handle_actuators_a, pattern='manage_light'),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                    CallbackQueryHandler(self.handle_bye, pattern='bye'),
                ],
                WAIT_ACTUATOR_STATE: [
                    CallbackQueryHandler(partial(self.handle_actuator_state, publisherMQTT=self.mqtt_client), pattern='on'),
                    CallbackQueryHandler(partial(self.handle_actuator_state, publisherMQTT=self.mqtt_client), pattern='off'),
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CONFIRM_X_BOTH: [
                    CallbackQueryHandler(self.confirm_delete_both, pattern='confirm_delete_both'),
                    CallbackQueryHandler(self.confirm_delete_both, pattern='cancel_delete_both'),
                ],
                FINAL_STAGE: [
                    CallbackQueryHandler(self.handle_back_to_main_menu, pattern='back_to_main_menu'),
                    CallbackQueryHandler(self.handle_bye, pattern='bye'),
                ],
                ConversationHandler.TIMEOUT: [
                    MessageHandler(filters.ALL, self.timeout_callback),
                    CallbackQueryHandler(self.timeout_callback)
                ]
            },
            fallbacks=[CommandHandler('start', self.start)],
            conversation_timeout=180 # Timeout: 3 minutes
        )

    ### Delete last keyboard
    async def delete_last_keyboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        # Attempt to retrieve the last bot message with a keyboard
        last_msg = self.user_data.get(user_id, {}).get("last_bot_msg")

        try:
            if last_msg and last_msg.reply_markup:
                await last_msg.edit_reply_markup(reply_markup=None)
        except Exception as e:
            print(f"[delete_last_keyboard] Couldn't remove old keyboard from last_msg: {e}")

        # # If an inline button was pressed, also attempt to remove the current keyboard from the callback
        # if update.callback_query:
        #     try:
        #         await update.callback_query.edit_message_reply_markup(reply_markup=None)
        #     except Exception as e:
        #         print(f"[delete_last_keyboard] Couldn't remove keyboard from callback_query: {e}")


    ## Start of the BOT
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        self.user_data[user_id] = {}
        self.alert_notifier.update_subscriptions("refresh") #"motion"

        await update.message.reply_text(f'*GREENHOUSE ALLA TERRONE*', parse_mode="Markdown")
        message = await update.message.reply_text(
            f"🌟 Welcome to the Greenhouse Management Bot! 🌱\n\n"
            f"Your unique ID is: `{user_id}`.\n"
            f"Please select an option from the menu below to get started:",
            reply_markup=main_menu_keyboard,
            parse_mode="Markdown"
        )
        self.user_data[user_id]["last_bot_msg"] = message
        self.user_data[user_id]['their_greenhouses'] = await self.check_gh_ownership(user_id, context.bot_data['catalog_url'])
        self.user_states[user_id] = MAIN_MENU
        return MAIN_MENU

    ############################## Callback Query Handlers ##############################
    async def handle_bye(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        #Resubscribe to the topics # Just to secure well functioning
        self.alert_notifier.update_subscriptions("refresh") #"motion" 

        user_id = update.effective_user.id
        self.user_data[user_id] = {}
        bye_msg = (
            "👋 Thank you for using our Greenhouse Management Bot! 🌱\n\n"
            "We hope you had a great experience managing your greenhouses and areas. If you have any feedback or need assistance, "
            "feel free to reach out to our support team or upgrade your plan. 💬\n\n"
            f"Take care of you, we take care of your plants.😊🌿🌞 See you next time! 🚀"
        )
        if update.message:
            await update.message.reply_text(bye_msg)
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(bye_msg, parse_mode="Markdown")
        self.user_states[user_id] = "END"
        return ConversationHandler.END

    async def handle_back_to_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        await self.delete_last_keyboard(update, context)
        if user_id in self.user_data:
            self.user_data[user_id] = {}

        query = update.callback_query
        if query:
            await query.answer()
            # await query.edit_message_reply_markup(reply_markup=None) # Remove the previous buttons from that message
            # Send a new message with text and new buttons
            message = await query.message.reply_text(
                " 👋 Welcome to the Main Menu! 🌱\n\n"
                "What would you like to do next? Please select an option below:",
                reply_markup=main_menu_keyboard
            )
        else:
            message = await update.message.reply_text(
                "👋  Welcome back to the Main Menu! 🌱\n\n"
                "What would you like to do next? Please select an option below:",
                reply_markup=main_menu_keyboard
            )
        self.user_data[user_id]["last_bot_msg"] = message
        self.user_states[user_id] = MAIN_MENU
        return MAIN_MENU

    ### Timeout callback to handle inactivity
    async def timeout_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        print(f"[TIMEOUT] Closing session for user {user_id}")
        await self.delete_last_keyboard(update, context) ####
        if user_id in self.user_data:
            del self.user_data[user_id]

        if update.message:
            await update.message.reply_text("⏳ Timeout. The conversation was closed due to inactivity.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("⏳ Timeout. The conversation was closed due to inactivity.")
        self.user_states[user_id] = "END"
        return ConversationHandler.END

    ########################## HANDLERS FOR THE STATE TRANSITIONS #########################
    ######################## CREATION PART ##########################
    ### Asks for a greenhouse ID for the new GH
    async def handle_wait_new_gh_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update._effective_user.id
        query = update.callback_query
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)  # Remove the previous keyboard

        message = await update.callback_query.message.reply_text(
            "🌟 *Create a New Greenhouse* 🌱\n\n"
            "Please enter a unique numeric ID for your greenhouse (maximum 5 digits). This ID will help us identify your greenhouse.\n\n",
            reply_markup=back_to_MM,
            parse_mode="Markdown"
        )
        self.user_data[user_id]["last_bot_msg"] = message
        self.user_states[user_id] = WAIT_NEW_GH_ID
        return WAIT_NEW_GH_ID

    ### Handle the input of a new greenhouse ID and check if it is valid, and asks for the plant type
    async def handle_check_gh_id_and_wait_new_gh_plant(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        catalog_url = context.bot_data['catalog_url']

        gh_id = update.message.text.strip()

        await self.delete_last_keyboard(update, context)

        if not (gh_id.isdigit() and len(gh_id) < 5):
            message = await update.message.reply_text(
                "🚫 *Invalid ID!*\n\n"
                "The ID must be numeric and contain a maximum of 5 digits. 🌱\n",
                reply_markup=back_to_MM,
                parse_mode="Markdown"
            )
            self.user_data[user_id]["last_bot_msg"] = message
            self.user_states[user_id] = WAIT_NEW_GH_ID
            return WAIT_NEW_GH_ID

        # Verify if the ID already exists in the database
        if await check_gh_id_exists(catalog_url, gh_id):
            message = await update.message.reply_text(
                "⚠️ *ID Already in Use!*\n\n"
                "The ID you entered is already associated with another greenhouse. Please choose another one. 🌱\n",
                reply_markup=back_to_MM,
                parse_mode="Markdown"
            )
            self.user_data[user_id]["last_bot_msg"] = message
            self.user_states[user_id] = WAIT_NEW_GH_ID
            return WAIT_NEW_GH_ID
        # If the ID is valid and does not exist, save it in user_data
        self.user_data[user_id]['new_gh_id'] = gh_id
        message = await update.message.reply_text(
            f"🎉 Great! The ID *{gh_id}* has been successfully reserved for your new greenhouse. 🌱\n\n"
            "*Now, let's design its first area! 🌟\n*"
            "Please tell me the type of plant you'd like to grow in this area (maximum 30 characters):",
            reply_markup=back_to_MM,
            parse_mode="Markdown"
        )
        self.user_data[user_id]["last_bot_msg"] = message
        self.user_states[user_id] = WAIT_PLANT
        return WAIT_PLANT

    ### Check the plant type inserted and ask for the first threshold (temperature)
    async def handle_plant_set_start_thresholds(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        thresholds = context.application.bot_data["default_thresholds"]

        plant_type = update.message.text.strip()
        await self.delete_last_keyboard(update, context)

        # Verify that the plant type does not exceed 30 characters
        if len(plant_type) > 30 or not re.match(r'^[a-zA-Z0-9 ]+$', plant_type):
            message = await update.message.reply_text(
                "🚫 Error: Max 30 characters. Use only letters, numbers and spaces.",
                reply_markup=back_to_MM
            )
            self.user_states[user_id] = WAIT_PLANT
            self.user_data[user_id]["last_bot_msg"] = message
            return WAIT_PLANT

        else:
            self.user_data[user_id]['plant_type'] = plant_type
            min_val, max_val, suggested = thresholds["temperature"]["min"], thresholds["temperature"]["max"], thresholds["temperature"]["suggested"]
            markup_option = await build_suggestion_keyboard(suggested)

            message = await update.message.reply_text(
                "\n".join([
                    "🌱 *Plant Type Accepted\\!* 🎉",
                    f"This area will be dedicated to growing *{escape_md_v2(plant_type)}*\\. 🌟",
                    "*Now, let\\'s configure some important parameters for your area\\.*",
                    "",
                    "Please enter the *maximum temperature* that can be tolerated for this area\\. 🌡️",
                    f"💡 ***Tip:*** Choose a value between *{escape_md_v2(min_val)}°C* and *{escape_md_v2(max_val)}°C*, or select the suggested value below\\."
                ]),
                reply_markup=markup_option,
                parse_mode="MarkdownV2"
            )
            self.user_data[user_id]['threshold_stage'] = 'temperature'
            self.user_states[user_id] = SET_THRESHOLDS
            self.user_data[user_id]["last_bot_msg"] = message
            return SET_THRESHOLDS
    
    ### Handle the input of thresholds for temperature, humidity, and light
    async def handle_threshold_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        stage_of_set = self.user_data[user_id]['threshold_stage']
        d_thresholds = context.application.bot_data["default_thresholds"]

        await self.delete_last_keyboard(update, context)

        # Get the value from button or text
        if update.callback_query:
            query = update.callback_query
            value_str = query.data
            await query.answer()
            # await query.edit_message_reply_markup(reply_markup=None)
        else:
            value_str = update.message.text.strip()
        # Convert to int
        try:
            value = int(value_str)
        except ValueError:
            await self.delete_last_keyboard(update, context)
            message = await update.message.reply_text("Please enter a valid number.",
                                            reply_markup=back_to_MM)
            self.user_data[user_id]["last_bot_msg"] = message
            self.user_states[user_id] = SET_THRESHOLDS
            return SET_THRESHOLDS
        
        min_val = d_thresholds[stage_of_set]["min"]
        max_val = d_thresholds[stage_of_set]["max"]
        suggested_val = d_thresholds[stage_of_set]["suggested"]
        unit = d_thresholds[stage_of_set]["unit"]

        if not (min_val <= value <= max_val):
            message = await update.message.reply_text(f"The value must be between *{min_val}{unit}* and *{max_val}{unit}*. Please try again or choose the recommended value.",
                            reply_markup=await build_suggestion_keyboard(suggested_val, include_back=False),
                            parse_mode="Markdown"
            )
            self.user_states[user_id] = SET_THRESHOLDS
            self.user_data[user_id]["last_bot_msg"] = message
            return SET_THRESHOLDS
        
        self.user_data[user_id][f"{stage_of_set}_threshold"] = value
  
        # Move to the next threshold
        if stage_of_set == 'temperature':
            self.user_data[user_id]['threshold_stage'] = 'humidity'
            return await self.ask_objective_threshold(update, context)
        elif stage_of_set == 'humidity':
            self.user_data[user_id]['threshold_stage'] = 'light'
            return await self.ask_objective_threshold(update, context)
        elif stage_of_set == 'light':
            text_shown = (
                f"✔ *Thresholds configured*:\n"
                f"🌡 *Temperature*: {self.user_data[user_id]['temperature_threshold']}{d_thresholds['temperature']['unit']}\n"
                f"💧 *Humidity*: {self.user_data[user_id]['humidity_threshold']}{d_thresholds['humidity']['unit']}\n"
                f"💡 *Light*: {self.user_data[user_id]['light_threshold']}{d_thresholds['light']['unit']}\n"
                "_Please wait while the request is being processed. Thank you!_"
            )
            if update.message:
                message = await update.message.reply_text(text_shown, parse_mode="Markdown")
            elif update.callback_query:
                message = await update.callback_query.message.reply_text(text_shown, parse_mode="Markdown")

            self.user_data[user_id]["last_bot_msg"] = message
            # If creating a new greenhouse and area for the first time
            if self.user_data[user_id].get('new_gh_id') is not None: #so add a new greenhouse with area
                return await self.handle_create_first_a(update, context)
            
            # If creating a new area in an existing greenhouse
            elif self.user_data[user_id].get('gh_to_manage') is not None: # so add a new area
                return await self.add_area_confirm(update, context)
            else:
                print(">> Internal error: issues between return functions")
        else:
            await update.message.reply_text("Internal error. Unrecognized stage. If the issue persists, contact support. Goodbye.")
            self.user_states[user_id] = "END"
            return ConversationHandler.END

    ### Iteratively ask for the objective threshold based on the current stage (temp, humidity, light)    
    async def ask_objective_threshold(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        stage_of_set = self.user_data[user_id]['threshold_stage']
        thresholds = context.application.bot_data["default_thresholds"]
        unit = thresholds[stage_of_set]["unit"]
        
        if stage_of_set == "humidity":
            min_val, max_val, suggested = thresholds["humidity"]["min"], thresholds["humidity"]["max"], thresholds["humidity"]["suggested"]
            label = "humidity"
        elif stage_of_set == "light":
            min_val, max_val, suggested = thresholds["light"]["min"], thresholds["light"]["max"], thresholds["light"]["suggested"]
            label = "luminosity"
        else:
            if update.message:
                await update.message.reply_text("Internal error: unknown stage. Please contact support.")
            elif update.callback_query:
                await update.callback_query.answer("Internal error: unknown stage. Please contact support.")
            self.user_states[user_id] = "END"
            return ConversationHandler.END

        await self.delete_last_keyboard(update, context) ####
        markup_option = await build_suggestion_keyboard(suggested)
        if update.message:
            message = await update.message.reply_text(
                f"Please enter the minimum threshold for *{label}* between *{min_val}{unit}* and *{max_val}{unit}*, or use the suggested value:",
                reply_markup=markup_option,
                parse_mode="Markdown"
            )
        elif update.callback_query:
            #await update.callback_query.answer()
            message = await update.callback_query.message.reply_text(
                f"Please enter the minimum threshold for *{label}* between *{min_val}{unit}* and *{max_val}{unit}*, or use the suggested value:",
                reply_markup=markup_option,
                parse_mode="Markdown"
            )
        self.user_data[user_id]["last_bot_msg"] = message
        self.user_states[user_id] = SET_THRESHOLDS
        return SET_THRESHOLDS

    ### Handle the addition of a new area in an existing greenhouse
    async def add_area_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        catalog_url = context.bot_data['catalog_url']

        greenhouse_id = self.user_data[user_id]['gh_to_manage']
        new_id = self.user_data[user_id]['new_area_id']
        plant_type = self.user_data[user_id]['plant_type']

        # Get the thresholds from user_data
        temperature_threshold = self.user_data[user_id]['temperature_threshold']
        humidity_threshold = self.user_data[user_id]['humidity_threshold']
        light_threshold = self.user_data[user_id]['light_threshold']

        if await create_area(catalog_url, greenhouse_id, new_id, plant_type, temperature_threshold, humidity_threshold, light_threshold):
            # Add to the map and update subscriptions
            await self.add_area_to_map(greenhouse_id, new_id)
            self.alert_notifier.update_subscriptions("create", greenhouse_id, new_id)

            text_shown = (
                f"🎉 *Success!* The new area has been added. 🌱\n\n"
                f"🆔 *Area ID:* `{self.user_data[user_id]['new_area_id']}`\n"
                f"🌱 *Plant Type:* `{plant_type}`\n\n"
                "You can now return to the main menu or continue managing your greenhouse. 🚀"
            )
            if update.message:
                message = await update.message.reply_text(text_shown, reply_markup=back_to_MM, parse_mode="Markdown")
            elif update.callback_query:
                message = await update.callback_query.message.reply_text(text_shown, reply_markup=back_to_MM, parse_mode="Markdown")
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            self.user_data[user_id]["last_bot_msg"] = message
            return FINAL_STAGE
        else:
            await update.message.reply_text("Error creating the area. Please try again.",
                                            reply_markup=(end_markup))
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return FINAL_STAGE

    ### Handle the creation of the first greenhouse and area
    async def handle_create_first_a(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        catalog_url = context.bot_data['catalog_url']
        user_id = update.effective_user.id
        gh_id = self.user_data[user_id]['new_gh_id']
        plant_type = self.user_data[user_id]['plant_type']
        # Get the thresholds from user_data
        temperature_threshold = self.user_data[user_id]['temperature_threshold']
        humidity_threshold = self.user_data[user_id]['humidity_threshold']
        light_threshold = self.user_data[user_id]['light_threshold']

        # Call the function to create the greenhouse and the area
        success = await create_greenhouse_and_area(catalog_url, user_id, gh_id, plant_type, temperature_threshold, humidity_threshold, light_threshold)
        
        if success:
            #Update the greenhouse_user_map and subscribe to the new topics
            await self.create_greenhouse_map(gh_id, 1, user_id) #1 is the first area
            self.alert_notifier.update_subscriptions("create", gh_id, 1) #"motion"
            del self.user_data[user_id]['new_gh_id']
            messagee = (
                f"✅ *Greenhouse Created Successfully!*\n"
                f"🆔 *ID*: `{gh_id}`\n"
                f"🌱 *First Area*: Plants of type: `{plant_type}`\n\n"
                f"Your greenhouse is now ready. Use the Main Menu to manage it."
            )
            if update.message:
                await update.message.reply_text(
                    messagee,
                    reply_markup=back_to_MM,
                    parse_mode="Markdown"
                )
            elif update.callback_query:
                await update.callback_query.message.reply_text(
                    messagee,
                    reply_markup=back_to_MM,
                    parse_mode="Markdown"
                )
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return MAIN_MENU
        else:
            errorrr = (
                "🚨 Oops! Something went wrong while creating your greenhouse. Please try again.\n"
                "If the issue persists, feel free to contact our support team for assistance. 🌱"
            )
            if update.message:
                await update.message.reply_text(
                    errorrr,
                    reply_markup=back_to_MM,
                    parse_mode="Markdown"
                )
            elif update.callback_query:
                await update.callback_query.message.reply_text(
                    errorrr,
                    reply_markup=back_to_MM,
                    parse_mode="Markdown"
                )
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return MAIN_MENU

    ######################## Manage and Delete combined part ######################
    ### List and select the GreenHouse to Manage/Delete
    async def handle_input_gh_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        query = update.callback_query
        await query.answer()  # Siempre respondé el callback aunque sea vacío
        await query.edit_message_reply_markup(reply_markup=None)
        self.user_data[user_id]['action'] = query.data

        if query.data == 'delete_greenhouse':
            cosa_fai = "delete"
        elif query.data == 'manage_greenhouses':
            cosa_fai = "manage"

        # List the user's greenhouses
        self.user_data[user_id]['their_greenhouses'] = await self.check_gh_ownership(user_id, context.bot_data['catalog_url'])
        # If the user has no greenhouses, send a message and return to the main menu
        if not self.user_data[user_id]['their_greenhouses']:
            message = await update.callback_query.message.reply_text(
                "It seems like you don't have any greenhouses yet. 🌱\n"
                "Please go back to the main menu and create one to get started!",
                reply_markup=back_to_MM
            )
            self.user_data[user_id]["last_bot_msg"] = message
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return MAIN_MENU
        
        # List the user's greenhouses and ask for the ID
        gh_list = "\n".join(
            f"-> {gh['greenhouseID']} (created on {gh['creation_date']})"
            for gh in sorted(self.user_data[user_id]['their_greenhouses'], key=lambda x: int(x['greenhouseID']))
        )
        message = await update.callback_query.message.reply_text(
            f"🌱 *Your Greenhouses:*\n\n{gh_list}\n\n"
            f"Please type the *ID* of the greenhouse you want to *{cosa_fai}*.\n", ### THIS COMMA
            reply_markup=back_to_MM,
            parse_mode="Markdown"
        )
        self.user_data[user_id]["last_bot_msg"] = message
        self.user_states[user_id] = HANDLING_GH_ID
        return HANDLING_GH_ID

        ### Chek if the user owns any greenhouse and return the list with the IDs and creation date
    
    ## Check if the user owns any greenhouse and return the list with the IDs and creation date
    async def check_gh_ownership(self, user_id, catalog_url) -> list:
        try:
            response = requests.get(f"{catalog_url}greenhouses")
            if response.status_code == 200:
                greenhouses = response.json().get("greenhouses", [])
                user_greenhouses = [
                    {
                        "greenhouseID": str(gh["greenhouseID"]),
                        "creation_date": gh.get("creation_date", "Unknown data")
                    }
                    for gh in greenhouses if gh.get("telegram_ID") == user_id
                ]
                self.user_data[user_id]['their_greenhouses'] = user_greenhouses
                return user_greenhouses
            self.user_data[user_id]['their_greenhouses'] = []
            return []
        except requests.exceptions.RequestException:
            return []

    ### Handle the selection of a greenhouse ID for management or deletion
    async def handle_gh_id_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
            user_id = update.effective_user.id
            await self.delete_last_keyboard(update, context) ####

            id_selected = update.message.text.strip()
            # Verify if the ID is valid, numeric, and has a maximum of 5 digits
            if not (id_selected.isdigit() and len(id_selected) < 5):
                message = await update.message.reply_text(
                    f"❌ Invalid ID entered! Please ensure the ID is numeric and contains a maximum of 5 digits.\n"
                    "_💡 Tip: Check the list of available greenhouses above and try again._",
                    reply_markup=(back_to_MM),
                    parse_mode="Markdown"
                )
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = HANDLING_GH_ID
                return HANDLING_GH_ID

            # Verify that the ID belongs to the user
            if not any(gh["greenhouseID"] == id_selected for gh in self.user_data[user_id]['their_greenhouses']):
                message = await update.message.reply_text(
                    "🚫 The greenhouse ID you entered does not exist or does not belong to you. 🌱\n"
                    "_💡 Please double-check the list of available greenhouses above and try again._",
                    reply_markup=back_to_MM,
                    parse_mode="Markdown"
                )
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = HANDLING_GH_ID
                return HANDLING_GH_ID

            action = self.user_data[user_id]['action']  # 'delete_greenhouse' or 'manage_greenhouses'

            # If the ID is valid and exists, save it in user_data
            if action == 'delete_greenhouse':
                self.user_data[user_id]['gh_to_delete'] = id_selected
                await update.message.reply_text(f"ID accepted! The greenhouse to delete is: {id_selected}.")
                message = await update.message.reply_text(
                    f"⚠️ Are you sure you want to permanently delete the greenhouse with ID: {id_selected}?\n"
                    "This action cannot be undone. Please confirm your choice:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ CONFIRM", callback_data='confirm_delete_gh')],
                        [InlineKeyboardButton("❌ CANCEL", callback_data='cancel_delete_gh')]
                    ])
                )
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = CONFIRM_X_GH
                return CONFIRM_X_GH

            elif action == 'manage_greenhouses':
                self.user_data[user_id]['gh_to_manage'] = id_selected
                message = await update.message.reply_text(
                    f"✅ You have selected the greenhouse with ID: {id_selected}.\n"
                    "What would you like to do next? 🌱",
                    reply_markup=areas_keyboard
                )
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = MANAGE_GH
                return MANAGE_GH

    ############################ Deleting an GH section #######################
    ### Delete Greenhouse
    async def handle_delete_gh(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        catalog_url = context.bot_data['catalog_url']
        greenhouse_to_delete = self.user_data[user_id]['gh_to_delete']

        query = update.callback_query
        await query.answer()  # Always respond to the callback, even if empty
        decision = query.data  # YES OR NO
        # await query.edit_message_reply_markup(reply_markup=None)
        await self.delete_last_keyboard(update, context) ####

        # If the user confirms deletion
        if decision == 'confirm_delete_gh':
            if await delete_entire_greenhouse(catalog_url, greenhouse_to_delete):             

                await self.delete_greenhouse_from_map(greenhouse_to_delete)
                self.alert_notifier.update_subscriptions("delete", greenhouse_to_delete) #"motion"

                message = await update.callback_query.message.reply_text(
                    f"✅ Greenhouse with ID: {greenhouse_to_delete} has been successfully deleted. 🌱\n"
                    "You can now return to the main menu to manage your other greenhouses or create a new one.",
                    reply_markup=back_to_MM
                )
                self.user_data[user_id]["last_bot_msg"] = message
                # Update the user's greenhouse list to reflect the deletion
                self.remove_greenhouses(user_id, greenhouse_to_delete)
                
                del self.user_data[user_id]['gh_to_delete']
                #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
                return MAIN_MENU
            else:
                message = await update.callback_query.message.reply_text(
                    "🚨 Oops! Something went wrong while trying to delete the greenhouse. 🌱\n"
                    "Please try again or contact support if the issue persists. 💡",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ CONFIRM", callback_data='confirm_delete_gh')],
                        [InlineKeyboardButton("❌ CANCEL", callback_data='cancel_delete_gh')],
                        [InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]
                    ])
                )
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] =  CONFIRM_X_GH
                return CONFIRM_X_GH

        elif decision == 'cancel_delete_gh':
            await update.callback_query.message.reply_text("Deletion canceled.")
            del self.user_data[user_id]['gh_to_delete']
            # Return to the main menu
            message = await update.callback_query.message.reply_text(
                "✅ Action canceled successfully. Return to the main menu.",
                reply_markup=back_to_MM
            )
            self.user_data[user_id]["last_bot_msg"] = message
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return MAIN_MENU
        else:
            await update.callback_query.message.reply_text(
                "⚠️ Invalid option selected. Please try again or contact support if the issue persists. Goodbye."
            )
            self.user_states[user_id] = "END"
            return ConversationHandler.END

    async def remove_greenhouse(self, user_id, greenhouse_id): #only from internal temporal list
        self.user_data[user_id]['their_greenhouses'] = [
            gh for gh in self.user_data[user_id]['their_greenhouses']
            if gh['greenhouseID'] != greenhouse_id
        ]

    ############################ Managing Greenhouse section #########################
    ### Manage Add area
    async def handle_add_area(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        catalog_url = context.bot_data['catalog_url']
        greenhouse_id = self.user_data[user_id]['gh_to_manage']

        await self.delete_last_keyboard(update, context) ####
        await update.callback_query.message.reply_text(
            "🌱 Great! Let's add a new area to your greenhouse. 🌟\n"
        )
        available_id = await next_area_id(catalog_url, greenhouse_id)

        if available_id == 0:
            message = await update.callback_query.message.reply_text(
                "🚫 *Maximum Areas Reached!*\n\n"
                "This greenhouse already has the maximum of 4 areas. 🌱\n"
                "To add more areas, you can either:\n"
                "_1️⃣ Create a new greenhouse._\n"
                "_2️⃣ Delete an existing area in this greenhouse._\n\n"
                "Please return to the main menu to proceed.",
                reply_markup=back_to_MM,
                parse_mode="Markdown"
            )
            self.user_data[user_id]["last_bot_msg"] = message
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return MAIN_MENU  # MANAGE_GH
        else:
            self.user_data[user_id]['new_area_id'] = available_id
            message = await update.callback_query.message.reply_text(
                f"😃 The new area will be assigned the ID: *{available_id}*.\n"
                f"Please enter the type of plant you want to grow in this area (maximum 30 characters):",
                reply_markup=back_to_MM,
                parse_mode="Markdown"
            )
            self.user_data[user_id]["last_bot_msg"] = message
            self.user_states[user_id] = WAIT_PLANT
            return WAIT_PLANT

    ### Manage Greenhouse (delete an area, manage areas, view historical data)
    async def handle_manage_gh(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        catalog_url = context.bot_data['catalog_url']
        greenhouse_id = self.user_data[user_id]['gh_to_manage']

        query = update.callback_query
        await query.answer()  #
        action = query.data
        # await query.edit_message_reply_markup(reply_markup=None)
        await self.delete_last_keyboard(update, context) ####

        self.user_data[user_id]['area_managing_desired_action'] = action

        # Get the areas
        areas = await list_areas(catalog_url, greenhouse_id)
        text_1 = (
            f"🌱 *Areas in Greenhouse ID: {greenhouse_id}*:\n\n" +
            "\n".join([f"🔹 *{area[0]} - {area[1]}*" for area in areas]) +
            "\n\n💡 _*Tip:* Select an area below to proceed._"
        )
        # Build markup for areas (buttons)
        buttons_areas = [
            InlineKeyboardButton(f"{area[0]} - {area[1]}", callback_data=f"area_{area[0]}")
            for area in areas
        ]
        markup_areas = [buttons_areas[i:i + 2] for i in range(0, len(buttons_areas), 2)]
        markup_areas.append([InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]) #keep this format

        # Text based on the action
        if action == 'storical_data_gh':
            message = await update.callback_query.message.reply_text(text_1,
                                                                     parse_mode="Markdown")
            self.user_data[user_id]["last_bot_msg"] = message
            return await handle_storical_data_gh(update, context)
        elif action == 'gestion_areas':
            prompt = f"Manage the areas of the greenhouse ID {greenhouse_id}:"
        elif action == 'eliminacion_area':
            prompt = f"Choose an area to delete from the greenhouse ID {greenhouse_id}:"
        else:
            prompt = f"Areas of the greenhouse ID {greenhouse_id}:"

        # Edit the original message to show text + buttons
        message = await query.edit_message_text(
            text=text_1 + "\n\n" + prompt,
            reply_markup=InlineKeyboardMarkup(markup_areas),
            parse_mode="Markdown"
        )
        self.user_data[user_id]["last_bot_msg"] = message
        self.user_states[user_id] = SHOWING_AVAILABLE_AREAS
        return SHOWING_AVAILABLE_AREAS

    ## According to the action selected, show the options for the areas  
    async def checking_what_to_do_showed_areas(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
            user_id = update.effective_user.id
            query = update.callback_query
            await query.answer()
            await query.edit_message_reply_markup(reply_markup=None)
            # await self.delete_last_keyboard(update, context) ####

            id_to_do = query.data.split("_")[1]  # Splits decision in ["area", "area_id"] and takes the [1]=id
            self.user_data[user_id]['area_to_do'] = id_to_do

            next_step = self.user_data[user_id]['area_managing_desired_action']

            # If the user chooses to manage areas
            if next_step == 'gestion_areas':
                message = await update.callback_query.message.reply_text(
                    f"🔍 *Monitoring & Control Menu*\n"
                    f"You have selected the area with ID: {id_to_do}. Choose what to do next:\n"
                    f"_(You can return or exit below)_\n"
                    f"1️⃣ *Sensors*\n"
                    f"2️⃣ *Actuators*\n",
                    parse_mode='Markdown',
                    reply_markup=A_Mg_markup
                )
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = WAIT_AREA_INSTRUCTION
                return WAIT_AREA_INSTRUCTION

            # If the user chooses to delete areas
            elif next_step == 'eliminacion_area':
                self.user_data[user_id]['area_to_delete'] = id_to_do
                message = await update.callback_query.message.reply_text(
                f"⚠️ *Confirmation Required*\n\n"
                f"Are you sure you want to delete the area with ID: *{id_to_do}*? This action cannot be undone. 🚨",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ CONFIRM", callback_data='confirm_delete_area')],
                    [InlineKeyboardButton("❌ CANCEL", callback_data='cancel_delete_area')]
                ]),
                parse_mode="Markdown"
                )
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = CONFIRM_X_A
                return CONFIRM_X_A

            else:
                await update.callback_query.message.reply_text(
                "❌ Invalid option selected. Please try again or contact support if the issue persists. 🙏",
                reply_markup=None
                )
                self.user_states[user_id] = "END"
                return ConversationHandler.END
    
    ### Add a new area to the new greenhouse
    async def handle_wait_new_a_plant(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
            user_id = update.effective_user.id
            catalog_url = context.bot_data['catalog_url']
            greenhouse_id = self.user_data[user_id]['gh_to_manage']
            new_id = self.user_data[user_id]['new_area_id']
            temperature_threshold = self.user_data[user_id]['temperature_threshold']
            humidity_threshold = self.user_data[user_id]['humidity_threshold']
            light_threshold = self.user_data[user_id]['light_threshold']

            plant_type = update.message.text.strip()
            await self.delete_last_keyboard(update, context) ####

            # Verify that the plant type does not exceed 30 characters
            if len(plant_type) > 30 or not plant_type.isalnum():
                message = await update.message.reply_text(
                "🚫 *Error:* The plant type must not exceed 30 characters and should only contain letters and numbers. 🌱\n"
                "💡 Please try again with a valid input.",
                reply_markup=back_to_MM,
                parse_mode="Markdown"
                )
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = ADD_A
                return ADD_A

            if await create_area(catalog_url, greenhouse_id, new_id, plant_type, temperature_threshold, humidity_threshold, light_threshold):
                #Update the greenhouse_user_map and subscribe to the new topics
                await self.add_area_to_map(greenhouse_id, new_id)
                self.alert_notifier.update_subscriptions("create", greenhouse_id, new_id) #"motion"

                message = await update.message.reply_text(
                f"✅ *Success!* The area has been created successfully. 🎉\n\n"
                f"🆔 *Area ID:* `{new_id}`\n"
                f"🌱 *Plant Type:* `{plant_type}`\n\n"
                "You can now return to the main menu or manage your greenhouse further.",
                reply_markup=back_to_MM,
                parse_mode="Markdown"
                )
                self.user_data[user_id]["last_bot_msg"] = message
                del self.user_data[user_id]['new_area_id']  # Remove the key from user_data
                #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
                return MAIN_MENU
            else:
                message = await update.message.reply_text(
                "🚨 *Error:* Something went wrong while creating the area. 🌱\n"
                "💡 Please try again or contact support if the issue persists.",
                reply_markup=back_to_MM,
                parse_mode="Markdown"
                )
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = ADD_A
                return ADD_A

    ### Delete an Area
    async def handle_delete_area(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        catalog_url = context.bot_data['catalog_url']
        greenhouse_id = self.user_data[user_id]['gh_to_manage']

        await self.delete_last_keyboard(update, context)
        # Check if the area to delete is the last one in the greenhouse
        areas = await list_areas(catalog_url, greenhouse_id)
        # If it is the last area, ask for confirmation to delete the greenhouse as well
        if len(areas) == 1:
            message = await update.callback_query.message.reply_text(
                "⚠️ *Warning: Last Area in Greenhouse*\n\n"
                "This is the last area in the greenhouse. Deleting it will also remove the entire greenhouse. 🚨\n\n"
                "Are you sure you want to proceed? This action cannot be undone. Please confirm your choice:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ CONFIRM DELETE BOTH", callback_data='confirm_delete_both')],
                    [InlineKeyboardButton("❌ CANCEL", callback_data='cancel_delete_both')]
                ]),
                parse_mode="Markdown"
            )
            self.user_data[user_id]["last_bot_msg"] = message
            self.user_states[user_id] = CONFIRM_X_BOTH
            return CONFIRM_X_BOTH
        else:
            return await self.confirm_delete_area(update, context)
    
    ## Confirm Deletion of Area or Greenhouse (Not the last one)
    async def confirm_delete_area(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        catalog_url = context.bot_data['catalog_url']
        user_id = update.effective_user.id
        greenhouse_id = self.user_data[user_id]['gh_to_manage']
        area_X = self.user_data[user_id]['area_to_delete']
        
        query = update.callback_query
        await query.answer() 
        decision = query.data
        # await query.edit_message_reply_markup(reply_markup=None)
        await self.delete_last_keyboard(update, context) ####

        if decision == 'confirm_delete_area':
            if await delete_area(catalog_url, greenhouse_id, area_X):
                #Update the greenhouse_user_map and unsubscribe from the topic
                await self.delete_area_from_map(greenhouse_id, area_X)
                self.alert_notifier.update_subscriptions("delete", greenhouse_id, area_X) #"motion"
                message = await update.callback_query.message.reply_text(f"Area with ID: {area_X} successfully deleted.",
                                                            reply_markup=end_markup)
                self.user_data[user_id]["last_bot_msg"] = message
                #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
                return FINAL_STAGE
            else:
                message = await update.callback_query.message.reply_text("Error deleting the area. Please try again. If the issue persists, contact support.",
                                                                         reply_markup=InlineKeyboardMarkup([
                                                                [InlineKeyboardButton("✅ CONFIRM", callback_data='confirm_delete_area')],
                                                                [InlineKeyboardButton("❌ CANCEL", callback_data='cancel_delete_area')],
                                                                [InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]
                                                            ]))
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = CONFIRM_X_A
                return CONFIRM_X_A
        elif decision == 'cancel_delete_area':
            await update.callback_query.message.reply_text("Deletion canceled.")
            del self.user_data[user_id]['area_to_delete']
            message = await update.callback_query.message.reply_text(
                "Return to the main menu.",
                reply_markup=end_markup
            )
            self.user_data[user_id]["last_bot_msg"] = message
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return FINAL_STAGE
        else:
            await update.callback_query.message.reply_text(f"Unexpected error. Please try again.\n If it persists, contact support. Goodbye!")
            self.user_states[user_id] = "END"
            return ConversationHandler.END

    ### Confirm Deletion of Area and Greenhouse (if last area)
    async def confirm_delete_both(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        catalog_url = context.bot_data['catalog_url']
        user_id = update.effective_user.id
        greenhouse_id = self.user_data[user_id]['gh_to_manage']
        area_X = self.user_data[user_id]['area_to_delete']
        
        query = update.callback_query
        await query.answer()
        decision = query.data
        # await query.edit_message_reply_markup(reply_markup=None)
        await self.delete_last_keyboard(update, context) ####

        if decision == 'confirm_delete_both':
            if await delete_entire_greenhouse(catalog_url, greenhouse_id):
                #Update the greenhouse_user_map and unsubscribe from the topics
                await self.delete_greenhouse_from_map(greenhouse_id)
                self.alert_notifier.update_subscriptions("delete", greenhouse_id) #"motion"

                await update.callback_query.message.reply_text(f"Greenhouse with ID: {greenhouse_id} and area with ID: {area_X} successfully deleted.")
                if any(gh['greenhouseID'] == greenhouse_id for gh in self.user_data[user_id]['their_greenhouses']):
                    self.remove_greenhouse(user_id, greenhouse_id)
                else:
                    print(f"Warning: Greenhouse {greenhouse_id} was not in the list for user {user_id}")
                del self.user_data[user_id]['area_to_delete']
                # Return to the main menu
                message = await update.callback_query.message.reply_text(
                    "Return to the main menu or Exit. 😄",
                    reply_markup=end_markup
                )
                self.user_data[user_id]["last_bot_msg"] = message
                #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
                return FINAL_STAGE
            else:
                message = await update.callback_query.message.reply_text("Error deleting the greenhouse. Please try again.",
                                                                reply_markup=InlineKeyboardMarkup([
                                                                [InlineKeyboardButton("✅ CONFIRM", callback_data='confirm_delete_both')],
                                                                [InlineKeyboardButton("❌ CANCEL", callback_data='cancel_delete_both')],
                                                                [InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]
                                                            ]))
                self.user_data[user_id]["last_bot_msg"] = message
                self.user_states[user_id] = "END"
                return CONFIRM_X_BOTH
        elif decision == 'cancel_delete_both':
            await update.callback_query.message.reply_text("Deletion canceled.")
            del self.user_data[user_id]['area_to_delete']
            # Return to the main menu
            message = await update.callback_query.message.reply_text(
                "Return to the main menu.",
                reply_markup=end_markup
            )
            self.user_data[user_id]["last_bot_msg"] = message
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return FINAL_STAGE  # OR MANAGE_GH IN A FUTURE UPDATE
        else:
            await update.callback_query.message.reply_text("Critical error. Please try again. Goodbye.")
            self.user_states[user_id] = "END"
            return ConversationHandler.END

    ########################### Sensors and Actuators section ##########################
    ### Verify the current values of the sensors
    async def handle_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        catalog_url = context.bot_data['catalog_url']
        user_id = update.effective_user.id
        greenhouse_id = self.user_data[user_id]['gh_to_manage']
        area_processing = self.user_data[user_id]['area_to_do']

        area = await get_area(catalog_url, greenhouse_id, area_processing)
        if area is None:
            message = await update.callback_query.message.reply_text(
                "❌ Error retrieving area data. Please try again or contact support.",
                reply_markup=end_markup
            )
            self.user_data[user_id]["last_bot_msg"] = message
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return FINAL_STAGE
        

        query = update.callback_query
        await query.answer() 
        to_verify = query.data

        # if query.message.reply_markup is not None:
        #     await self.delete_last_keyboard(update, context) ####

        if to_verify == 'check_temperature':
            variable = "temperature"
            current_value = area.get('currentTemperature', 'Unknown')
        elif to_verify == 'check_humidity':
            variable = "humidity"
            current_value = area.get('currentHumidity', 'Unknown')
        elif to_verify == 'check_luminosity':
            variable = "luminosity"
            current_value = area.get('currentLuminosity', 'Unknown')

        config_key = "light" if variable == "luminosity" else variable
        unit = context.bot_data['default_thresholds'][config_key]['unit']

        await query.edit_message_reply_markup(reply_markup=None)
        message = await update.callback_query.message.reply_text(
            f"📟 *Current Status:*\n"
            f"🌱 *Greenhouse ID:* `{greenhouse_id}` 📍 *Area ID:* `{area_processing}`\n 🔍 *{variable.capitalize()}:* `{current_value} {unit}`\n\n"
            f"💡 *What would you like to do next?*",
            parse_mode="Markdown",
            reply_markup=A_Mg_markup
        )
        self.user_data[user_id]["last_bot_msg"] = message
        self.user_states[user_id] = WAIT_AREA_INSTRUCTION
        return WAIT_AREA_INSTRUCTION

    ### Manage Actuators asking the user what to do, turn ON or OFF
    async def handle_actuators_a(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        greenhouse_id = self.user_data[user_id]['gh_to_manage']
        area_processing = self.user_data[user_id]['area_to_do']

        query = update.callback_query
        await query.answer()  # Always respond to the callback even if empty
        actuator_selection = query.data
        self.user_data[user_id]['actuator_selection'] = actuator_selection

        # await query.edit_message_reply_markup(reply_markup=None)
        await self.delete_last_keyboard(update, context) ####

        if actuator_selection == 'manage_pump':
            macchinetta = "pump system"
        elif actuator_selection == 'manage_light':
            macchinetta = "light system"
        elif actuator_selection == 'manage_fan':
            macchinetta = "ventilation system"
        
        message =await update.callback_query.message.reply_text(
            f"🌟 *Control Actuator*\n"
            f"You have selected the *{macchinetta}* in Area *{area_processing}* of Greenhouse *{greenhouse_id}*.\n"
            f"Would you like to turn it *ON* or *OFF*? 🤔",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Turn ON", callback_data='on'),
                InlineKeyboardButton("❌ Turn OFF", callback_data='off')],
                [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='back_to_main_menu')]
            ]),
            parse_mode="Markdown"
        )
        self.user_data[user_id]["last_bot_msg"] = message
        self.user_states[user_id] = WAIT_ACTUATOR_STATE
        return WAIT_ACTUATOR_STATE

    ### Handle the state of the actuator (ON or OFF) and show the results according to the user request
    async def handle_actuator_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE, publisherMQTT) -> int:
        catalog_url = context.bot_data['catalog_url']
        user_id = update.effective_user.id
        greenhouse_id = self.user_data[user_id]['gh_to_manage']
        area_processing = self.user_data[user_id]['area_to_do']
        actuator_selection = self.user_data[user_id]['actuator_selection']
        system = "Pump" if actuator_selection == 'manage_pump' else "Light" if actuator_selection == 'manage_light' else "Fan"

        query = update.callback_query
        # await query.edit_message_reply_markup(reply_markup=None)
        await self.delete_last_keyboard(update, context) ####
        await query.answer()
        to_set_on_off = query.data  # ON or OFF\

        #Check if the actuator is already on or off
        state_a = await check_actuator_state(catalog_url, greenhouse_id, area_processing, actuator_selection)
        self.user_data[user_id]['actuator_state'] = state_a

        if actuator_selection == 'manage_pump':
            oki = await self.set_actuator(update, greenhouse_id, area_processing, "pumpActuation",to_set_on_off, publisherMQTT)
        elif actuator_selection == 'manage_light':
            oki = await self.set_actuator(update, greenhouse_id, area_processing, "lightActuation", to_set_on_off, publisherMQTT)
        elif actuator_selection == 'manage_fan':
            oki = await self.set_actuator(update, greenhouse_id, area_processing, "ventilationActuation", to_set_on_off, publisherMQTT)
        else:
            await update.callback_query.message.reply_text("Invalid actuator. Please try again.",
                                                        reply_markup=end_markup
            )
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return FINAL_STAGE #ONLY TWO OPTIONS OF BUTTONS
        
        #check if to_set_on_off is 1 or 0 and convert it to on or off for showing to the user
        to_set_on_off_show = normalize_state_to_str(to_set_on_off)

        # Check the response from the MQTT publish
        if isinstance(oki, dict) and oki.get("status_ok") == "nochange":
            message = await update.callback_query.message.reply_text(
                f"ℹ️ The actuator is already set to *{normalize_state_to_str(state_a)}*. No changes were made. ✅\n"
                "You can return to the Main Menu or perform another action.",
                reply_markup=end_markup,
                parse_mode="Markdown"
            )
            #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
            return MAIN_MENU
        elif isinstance(oki, dict) and oki.get("status_ok") == True:
            message = await update.callback_query.message.reply_text(
                f"✅ Success! The actuator *{system}* in Area *{area_processing}* of Greenhouse *{greenhouse_id}* is now set to *{to_set_on_off_show}*. 🎉",
                reply_markup=end_markup,
                parse_mode="Markdown"
            )

        elif isinstance(oki, dict) and oki.get("status_ok") == False:
            message = await update.callback_query.message.reply_text(
                f"⚠️ Oops! There was an error sending the MQTT command. 🚨\n"
                f"Error details: *{oki.get('error', 'Unknown error.')}*.\n"
                "Please try again or contact support if the issue persists. 🙏",
                reply_markup=end_markup,
                parse_mode="Markdown"
            )
        self.user_data[user_id]["last_bot_msg"] = message
        #NO UPDATE OF USER_STATE, IT'S MADE IN THE handle_back_to_main_menu
        return FINAL_STAGE

    ### Checks if the wanted state is different an sets the actuator state (ON or OFF) using MQTT.
    async def set_actuator(self, update, greenhouse_id, area_processing, actuator_type, to_set_on_off, publisherMQTT):
        user_id = update.effective_user.id
        state_previous = self.user_data[user_id]['actuator_state']
        action_wanted = to_set_on_off


        if normalize_state_to_int(state_previous) == normalize_state_to_int(action_wanted):
                return {"status_ok": "nochange", "status_code": "alreadySET"}
        else:
            try:
                # Construct the topic based on the actuator type
                if actuator_type == "pumpActuation":
                    topic = f"greenhouse{greenhouse_id}/area{area_processing}/actuation/pump"
                elif actuator_type == "lightActuation":
                    topic = f"greenhouse{greenhouse_id}/area{area_processing}/actuation/light"
                elif actuator_type == "ventilationActuation":
                    topic = f"greenhouse{greenhouse_id}/area{area_processing}/actuation/ventilation"
                else:
                    message = await update.callback_query.message.reply_text(
                        "⚠️ Oops! It seems like the selected actuator type is invalid. 🌱\n"
                        "💡 Please try again or contact support if the issue persists. Thank you for your patience! 🙏",
                        reply_markup=end_markup
                    )
                    self.user_data[user_id]["last_bot_msg"] = message
                    return {"status_ok": False, "status_code": "noactuatorType"}
                
                #Normalize the action_wanted to the expected format
                #state_a is 0 or 1 for "pump or ventialation" and on or off for light, info from the other microsevice.
                if actuator_type == "lightActuation":
                    payload = {"state": action_wanted.lower()}  # if it's STRING "on" or "off", convert to lowercase.
                else:
                    payload = {"state": normalize_state_to_int(action_wanted)}  # if it's INT, just in case normalize.

                response = publisherMQTT.myPublish(topic, payload)
                if response["status_code"] != 200:
                    print("Error publishing MQTT message:", response.get("error"))

                if isinstance(response, dict):
                    status = response.get("status_code")
                    if status == 200:
                        return {"status_ok": True, "status_code": status}
                    else:
                        return {"status_ok": False, "status_code": status}
                else:
                    return {"status_ok": False, "status_code": "Unknown"}
            except Exception as e:
                print(f"Error while setting actuator state: {e}")
                message = await update.callback_query.message.reply_text(
                    "🚨 Oops! Something went wrong while trying to set the actuator state. 🌱\n"
                    "💡 Please try again or contact support if the issue persists. Thank you for your patience! 🙏",
                    reply_markup=end_markup
                )
                self.user_data[user_id]["last_bot_msg"] = message
                return {"status_ok": False, "status_code": "Fatal"}
        
    ################################## ALERTS MANAGEMENT #####################################
    ########## Dictionary/Map to store user-specific alerts ###########
    ## Initializes the greenhouse map section for the current user
    async def create_greenhouse_map(self, gh_id, area_id, current_user):
        async with self.greenhouse_map_lock:
            gh_entry = self.greenhouse_user_map.get(gh_id)
            if gh_entry:
                if gh_entry['user'] != current_user:
                    # The GH changed owner => restart it in our permanent map
                    self.greenhouse_user_map[gh_id] = {'user': current_user, 'areas': {}}
            else:
                # First time we see this greenhouse
                self.greenhouse_user_map[gh_id] = {'user': current_user, 'areas': {}}
            # Initialize the area
            self.greenhouse_user_map[gh_id]["areas"][area_id] = {
                'LastMotionValue': None,
                'timestampMotion': None
            }

    ## Adds a new area to the greenhouse map for the current user
    async def add_area_to_map(self, gh_id, area_id):
        async with self.greenhouse_map_lock:
            gh_entry = self.greenhouse_user_map.get(gh_id)
            if not gh_entry:
                print(f"Greenhouse {gh_id} not found in the map. This should not happen.")
                return False 
            # Add an area if it does not exist
            if area_id not in gh_entry['areas']:
                gh_entry['areas'][area_id] = {'LastMotionValue': None, 'timestampMotion': None}
                print(f"Area {area_id} added to greenhouse {gh_id}.")
                return True
            else:
                print(f"Area {area_id} already exists in greenhouse {gh_id}. This should not happen.")
                return False

    ## Deletes a greenhouse from the map      
    async def delete_greenhouse_from_map(self, gh_id):
        async with self.greenhouse_map_lock:
            if gh_id in self.greenhouse_user_map:
                del self.greenhouse_user_map[gh_id]
                print(f"Greenhouse {gh_id} removed from the map.")
                return True
            else:
                print(f"Greenhouse {gh_id} not found in the map. This should now happen. Line 1719")
                return False

    ## Deletes an area from the greenhouse map for the current user   
    async def delete_area_from_map(self, gh_id, area_id):
        async with self.greenhouse_map_lock:
            gh_entry = self.greenhouse_user_map.get(gh_id)
            if not gh_entry:
                print(f"Greenhouse {gh_id} not found in the map. This should not happen. Line 1726")
                return False
            area_entry = gh_entry['areas'].get(area_id)
            if not area_entry:
                print(f"Area {area_id} not found in greenhouse {gh_id}. This should not happen.")
                return False
            del gh_entry['areas'][area_id]
            print(f"Area {area_id} removed from greenhouse {gh_id}.")
            return True

    ########## Alert Producer, Updater and Consumer ###########
    ## Alert Producer: Distributes alerts from the general queue to the user-specific dictionary pending alerts
    # if needed.
    async def alert_producer(self, alert_queue):
        while True:
            try:
                self.alert_data = await alert_queue.get()
                problem  = await self.update_dictionary(self.alert_data) 

                if self.alert_data:
                    chat_id = self.alert_data.get("chat_id")
                    await asyncio.sleep(0.1)
                    if chat_id:
                        if problem == True:
                            if chat_id not in self.pending_alerts:
                                print("el id habia sido elminado, lo agregamos")
                                self.pending_alerts[chat_id] = []
                            self.pending_alerts[chat_id].append(self.alert_data)
                            print("agregada la alerta al pendiente de 1752::", chat_id)
                            # self.pending_alerts.setdefault(chat_id, []).append(self.alert_data)
                            print(f"[✓] New alert added to pending for {chat_id}")
                        else:
                            print(f"[✓] No change detected for alert for {chat_id}, not adding to pending alerts.")
                    else:
                        print("[!] No chat_id found in alert data.")
                else:
                    print("[!] No alert data received.")
                    continue
                
                # Mark the task as done
                alert_queue.task_done()
            except asyncio.CancelledError:
                print("[!] Alert producer task cancelled.")
                break
            except Exception as e:
                print(f"[ERROR] Exception in alert_producer: {e}")

    ## Alert Updater: Handles the alert_data and returns True if there's a new emergency/problem
    # so the alert producer puts it in the pending_alerts dictionary.
    async def update_dictionary(self, alert_data): 
        topicbase = alert_data.get("bn", "")
        event = alert_data.get("e", [{}])[0]  # Consider only the first event in the SenML format.
        GH_ID, AREA_ID = get_ids(topicbase)
        alerttype = event.get("n", "")
        # Case 1: Alert in SenML format (MQTT with 'e') - Humidity, Temperature, Luminosity.
        # if alertype in ["temperature", "humidity", "luminosity"]:   
        #     GH_ID, AREA_ID = get_ids(topicbase)
        #     if not GH_ID or not AREA_ID:
        #         return False

        #     async with self.greenhouse_map_lock:
        #         if GH_ID not in self.greenhouse_user_map or AREA_ID not in self.greenhouse_user_map[GH_ID]["areas"]:
        #             print(f"Greenhouse {GH_ID} or Area {AREA_ID} not found in the map. This should not happen.") 
        #             return False

        #     situation = event.get("n")
        #     timestamp = event.get("t")
        #     value_received = None
        #     if situation == "motion":
        #         value_received = event.get("v")  # 1 o 0
        #         changed, value = await self.update_alert_value(GH_ID, AREA_ID, value_received, timestamp)
        #         if changed == True and value == 1:
        #             return True  # there was a change,  AND it changed from 0 to 1, send data. Not from 1 to 0.
        #         else:
        #             print("No update needed for this last alert.")
        #             return False
        #     else:
        #         print("Situation is not motion")
        #         return False #####
            # In the future updates, the extreme values of temperature, humidity, and luminosity will be added here.

        # Case 2: Alert in simple format (ONLY: "motion":"on")
        print("alerttype:", alerttype)
        if alerttype == "motion":
            value_raw = event.get("v")  # 1 or 0
            if value_raw is None:
                print("[MQTT] Missing value.")
                return False
            # Se aceptan todos los cambios sin verificar el último estado
            try:
                value_int = normalize_state_to_int(value_raw)
            except Exception as e:
                print(f"[MQTT] Error al convertir valor a int: {e}")
                return False

            async with self.greenhouse_map_lock:
                self.greenhouse_user_map[GH_ID]["areas"][AREA_ID]["LastMotionValue"] = value_int
                self.greenhouse_user_map[GH_ID]["areas"][AREA_ID]["timestampMotion"] = None  # No timestamp

            print("Motion received and put in the map antes del pending.")
            return True
        
    ## Update Alert Value: Updates the LastValue in the map after receiving a message from the broker
    # and returns True if the value changed from 0 to 1, False otherwise.
    # async def update_alert_value(self, gh_id, area_id, value_received,timestamp):
    #     async with self.greenhouse_map_lock:
    #         last_value = self.greenhouse_user_map[gh_id]["areas"][area_id]["LastMotionValue"]
    #         if last_value is None or value_received is None:
    #             print("[ERROR] One of the values is None.")
    #             return False, None
    #         try:
    #             last_value_int = normalize_state_to_int(last_value)
    #             value_received_int = normalize_state_to_int(value_received)
    #         except Exception as e:
    #             print(f"Error al convertir valores a int: {e}")
    #             return False, None
    #         # Update the motion value in the map
    #         self.greenhouse_user_map[gh_id]["areas"][area_id]["LastMotionValue"] = value_received_int
    #         self.greenhouse_user_map[gh_id]["areas"][area_id]["timestampMotion"] = timestamp

    #         if int(last_value_int) == int(value_received_int):
    #             #"No change detected in motion value".
    #             return False, None  # Only updated the dictionary, No need for sending an alert
    #         return True, value_received_int  # Update successful, value changed, and the value.

    ## Alert Consumer: Processes the pending alerts for each user and sends them via Telegram
    ## Alert Consumer: Processes the pending alerts for each user and sends them via Telegram
    async def alert_consumer(self, application, user_states):
        self.retry_flags = {}

        async def process_single_alert(chat_id):
            ##Processes only one alert for a specific user
            alert_info = self.pending_alerts[chat_id][0]
            text = format_alert_message(alert_info, self.retry_flags.get(chat_id, False))
            try:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='Markdown'
                )
                if self.pending_alerts[chat_id]:
                    self.pending_alerts[chat_id].pop(0)
                self.retry_flags[chat_id] = False

                if chat_id not in self.pending_alerts: ## DEBUG
                    print(" no hay chat_id ahhhhh")

                if not self.pending_alerts[chat_id]: #THIS SHOULD BE COMMENTED
                    print(f"[✓] All alerts processed for {chat_id}, cleaning up.")
                    self.pending_alerts.pop(chat_id, None)

            except Exception as e:
                print(f"Error sending alert to {chat_id}: {e}")
                if self.retry_flags.get(chat_id, False):
                    print(f"[✗] Second attempt failed for {chat_id}, discarding alert.")
                    if self.pending_alerts[chat_id]:
                        self.pending_alerts[chat_id].pop(0)
                    self.retry_flags[chat_id] = False
                else:
                    print(f"[!] Retrying alert for {chat_id} in next cycle...")
                    self.retry_flags[chat_id] = True
                    # No sleep aquí, se reintentará en la siguiente iteración del loop principal

        while True:
            try:
                tasks = []
                for chat_id in list(self.pending_alerts.keys()):
                    if self.pending_alerts[chat_id]:  # Solo si hay alertas
                        state = user_states.get(chat_id)
                        print("usuario en estado" , state)
                        if state in ["END", MAIN_MENU]:
                            tasks.append(asyncio.create_task(process_single_alert(chat_id)))
                        else:
                            print(f"User {chat_id} is in state {state}, alerts will not be displayed yet.")

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            print(f"[ERROR] Error in a task: {result}")
                
                await asyncio.sleep(2.5)
            except Exception as e:
                print(f"[ERROR] General error in alert_consumer: {e}")

    async def debug_loop(self):
        while True:
            print("[DEBUG] Bot sigue vivo")
            await asyncio.sleep(10)



    ### RUN METHOD FOR THE BOT
    def run(self):
        # Functions that work in parallel with the ConversationHandler
        async def start_alert_task(application):
            application.create_task(
                self.alert_producer(self.alert_queue)
            )
            application.create_task(
                self.alert_consumer(application, self.user_states)
            )
            application.create_task(
                self.update_registration_service()
            )
            application.create_task(
                self.debug_loop()
            )
        self.application.post_init = start_alert_task
        self.application.run_polling()
 
if __name__ == "__main__":
    config = load_config()
    bot = BotMain(config)
    # Run the bot
    bot.run()

##### NEIS RODRIGO AGUSTIN
##### s337958@studenti.polito.it
##### UNIVERSIDAD NACIONAL DE CÓRDOBA AND POLITÉCNICO DI TORINO
##### ARGENTINA - ITALY
##### 2024-2025
##### Programming for IOT applications