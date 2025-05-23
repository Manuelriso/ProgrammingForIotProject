import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from datetime import datetime
import MyMQTTforBOT as MyMQTTforBOT
from functools import partial #for inserting parameters in callbacks

# Estados del árbol de conversación
# MAIN_MENU, CREATE_GH, CREATE_A, INPUT_GH_ID, MANAGE_GH, MANAGE_AREA, CONFIRM_X_GH, ADD_A, DELETE_A, CONFIRM_X_A,  CONFIRM_X_BOTH = range(11)
MAIN_MENU, WAIT_NEW_GH_ID, WAIT_PLANT, CHECK_FIRST_THRESHOLD, SET_THRESHOLDS, CREATE_A, INPUT_GH_ID, HANDLING_GH_ID, CONFIRM_X_GH, MANAGE_GH, SHOWING_AVAILABLE_AREAS, CONFIRM_X_A, CONFIRM_X_BOTH, ADD_A, WAIT_AREA_INSTRUCTION, WAIT_ACTUATOR_STATE, FINAL_STAGE = range(17)

#STATES PER 

# Diccionario temporal por usuario
user_data = {}
######################### CONFIGURATION #########################
def load_config():
    with open('configBot.json') as config_file:
        config = json.load(config_file)
    return config

######################### Keyboards #########################
## Main menu keyboard
main_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("ADD GREENHOUSE", callback_data='add_greenhouse')],
    [InlineKeyboardButton("MANAGE GREENHOUSES", callback_data='manage_greenhouses')],
    [InlineKeyboardButton("DELETE GREENHOUSE", callback_data='delete_greenhouse')],
    [InlineKeyboardButton("BYE", callback_data='bye')]
])
## Back to main menu keyboard
back_to_MM = InlineKeyboardMarkup([
            [InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]
        ])
bye_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("BYE", callback_data='bye')]
        ])

end_markup = InlineKeyboardMarkup(back_to_MM.inline_keyboard + bye_button.inline_keyboard)

# A_Mg_markup = InlineKeyboardMarkup([
#             [InlineKeyboardButton("VERIFY HUMIDITY", callback_data='check_humidity')],
#             [InlineKeyboardButton("VERIFY TEMPERATURE", callback_data='check_temperature')],
#             [InlineKeyboardButton("VERIFY LUMINOSITY", callback_data='check_luminosity')],
#             [InlineKeyboardButton("MANAGE PUMP", callback_data='manage_pump')],
#             [InlineKeyboardButton("MANAGE FAN", callback_data='manage_fan')],
#             [InlineKeyboardButton("MANAGE LIGHT", callback_data='manage_light')],
#             [InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')],
#             [InlineKeyboardButton("BYE", callback_data='bye')]
#         ]) 

A_Mg_markup = InlineKeyboardMarkup([
    # Sensores (3 en una fila)
    [InlineKeyboardButton("HUMIDITY 🌫️", callback_data='check_humidity'),
     InlineKeyboardButton("TEMPERATURE 🌡️", callback_data='check_temperature'),
     InlineKeyboardButton("LUMINOSITY ☀️", callback_data='check_luminosity')],
    
    # Actuadores (3 en una fila)
    [InlineKeyboardButton("PUMP 💧", callback_data='manage_pump'),
     InlineKeyboardButton("FAN 🌬️", callback_data='manage_fan'),
     InlineKeyboardButton("LIGHT 💡", callback_data='manage_light')],
    
    # Opciones generales (2 en una fila)
    [InlineKeyboardButton("BACK 🔙", callback_data='back_to_main_menu'),
     InlineKeyboardButton("BYE 👋", callback_data='bye')]
])


######################### AUXILIARY FUNCTIONS #########################
### Verify if the greenhouse ID exists in the database
import requests

async def check_gh_id_exists(catalog_url, greenhouse_id) -> bool:
    try:
        response = requests.get(f"{catalog_url}greenhouses", timeout=5)
        if response.status_code == 200:
            greenhouses = response.json().get("greenhouses", [])
            print("IDs in catalog:", [gh['greenhouseID'] for gh in greenhouses])
            print("Checking ID:", greenhouse_id)
            result = any(int(gh['greenhouseID']) == int(greenhouse_id) for gh in greenhouses)
            print("Exists:", result)
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
        # Define the structure of the greenhouse to be created
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
        print(f"Sending POST request to: {catalog_url}greenhouse")
        response = requests.post(f"{catalog_url}greenhouse", json=new_greenhouse)  # POST request ###singular
        print(f"Status code: {response.status_code}")
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

### Chek if the user owns any greenhouse and return the list with the IDs and creation date
async def check_gh_ownership(user_id, catalog_url) -> list:
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
            user_data[user_id]['their_greenhouses'] = user_greenhouses
            return user_greenhouses
        user_data[user_id]['their_greenhouses'] = []
        return []
    except requests.exceptions.RequestException:
        return []

### Check the next area ID to be used while creating a new area
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

### Delete an entire greenhouse (maybe unify with delete area and work with callback to know what)
async def delete_entire_greenhouse(catalog_url, greenhouse_id) -> bool:
    try:
        response = requests.delete(f"{catalog_url}greenhouse/{greenhouse_id}")
        print(f"Response content: {response.text}")
        if response.status_code == 204: ##TO check
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False
    
### Delete an area inside a greenhouse  
async def delete_area(catalog_url, greenhouse_id, area_id) -> bool:
    try:
        response = requests.delete(f"{catalog_url}greenhouse{greenhouse_id}/area/{area_id}")
        if response.status_code == 204: ##TO check
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False

async def list_areas(catalog_url, greenhouse_id) -> list:
        try:
            response = requests.get(f"{catalog_url}greenhouse{greenhouse_id}/areas")
            print(f"URL: {catalog_url}greenhouse{greenhouse_id}/areas")  # Debug URL
            #print(f"Server response: {response.text}")  # Additional debug
            if response.status_code == 200:
                data = response.json()  # Get the response body
                areas = data.get("areas", [])  # Ensure 'areas' exists and is a list
                #print(f"Obtained areas: {areas}")  # Show the areas retrieved from the server
                if not areas:
                    # If no areas exist, notify and return an empty list
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

# Get the user id from a greenhouse id
async def get_user_id_from_gh_id(catalog_url, greenhouse_id) -> int:
    try:
        response = requests.get(f"{catalog_url}greenhouses/{greenhouse_id}")
        if response.status_code == 200:
            greenhouse = response.json()
            return greenhouse.get("telegram_ID")
        return None
    except requests.exceptions.RequestException:
        return None

async def remove_greenhouse(user_id, greenhouse_id): #only from internal temporal list
    user_data[user_id]['their_greenhouses'] = [
        gh for gh in user_data[user_id]['their_greenhouses']
        if gh['greenhouseID'] != greenhouse_id
    ]

async def build_suggestion_keyboard(suggested_value: int, include_back: bool = True) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(f"Suggested: {suggested_value}", callback_data=str(suggested_value))]]
    if include_back:
        keyboard.append([InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')])
    return InlineKeyboardMarkup(keyboard)

############################### CONVERSATION STATES ###############################
# Start of the BOT
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data[user_id] = {}
    await update.message.reply_text('GREENHOUSE ALLA TERRONE', reply_markup=ReplyKeyboardRemove())
    # Reply keyboard in the text area
    await update.message.reply_text(f"Welcome! Your ID is {user_id}. What would you like to do?", reply_markup=main_menu_keyboard)
    user_data[user_id]['their_greenhouses'] = await check_gh_ownership(user_id, context.bot_data['catalog_url'])
    return MAIN_MENU

####### CREATION PART ##########
### Handle the addition/creation of a greenhouse ID
async def handle_wait_new_gh_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> You entered handle_wait_new_gh_id")

    await update.callback_query.message.reply_text(
        "Please enter a numeric ID (maximum 5 digits), or press BACK to return to the main menu.",
        reply_markup=back_to_MM
    )
    return WAIT_NEW_GH_ID

async def handle_check_gh_id_and_wait_new_gh_plant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> You entered handle_check_gh_id_and_wait_new_gh_plant")
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']

    gh_id = update.message.text.strip()
    
    if not (gh_id.isdigit() and len(gh_id) < 5):
        await update.message.reply_text("Invalid ID. It must be numeric and have a maximum of 5 digits. Please try again.",
        reply_markup=back_to_MM 
        )
        return WAIT_NEW_GH_ID
    # Verify if the ID already exists in the database
    if await check_gh_id_exists(catalog_url, gh_id):
        await update.message.reply_text("This ID is already in use. Please choose another one.",
        reply_markup=back_to_MM                      
        )
        return WAIT_NEW_GH_ID
    # If the ID is valid and does not exist, save it in user_data
    user_data[user_id]['new_gh_id'] = gh_id
    await update.message.reply_text(
        f"ID accepted! Your greenhouse will have the ID: {gh_id}.\n"
        "Let's design its first area!\n"
        "Please enter the type of plant for the area (maximum 30 characters):",
        reply_markup=(back_to_MM)
    )
    return WAIT_PLANT

### Create the first area of the greenhouse
async def handle_plant_set_start_thresholds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> You entered a handle_set_thresholds. The plant type is being tested.")
    user_id = update.effective_user.id
    # catalog_url = context.bot_data['catalog_url']
    # gh_id = user_data[user_id]['new_gh_id']
    thresholds = context.application.bot_data["default_thresholds"]

    plant_type = update.message.text.strip()
    # Verify that the plant type does not exceed 30 characters
    if (len(plant_type) > 30 or not plant_type.isalnum()):
        await update.message.reply_text("Error: Do not exceed 30 characters, only letters and numbers are allowed. Please try again.",
        reply_markup=(back_to_MM)
        )
        return WAIT_PLANT
    else:
        user_data[user_id]['plant_type'] = plant_type
        min_val, max_val, suggested = thresholds["temperature"]["min"], thresholds["temperature"]["max"], thresholds["temperature"]["suggested"]
        markup_option = await build_suggestion_keyboard(suggested)

        # Ask for the temperature threshold/objective
        await update.message.reply_text(
            f"Plant type accepted! This area will contain plants of type: {plant_type}.\n"
            f"Let's set up some parameters.\n"
            f"Please insert the temperature desired between {min_val} y {max_val} or choose the suggested:",
            reply_markup=markup_option
        )
        user_data[user_id]['threshold_stage'] = 'temperature'
        return SET_THRESHOLDS

async def ask_objective_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stage_of_set = user_data[user_id]['threshold_stage']
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
        return ConversationHandler.END

    markup_option = await build_suggestion_keyboard(suggested)
    if update.message:
        await update.message.reply_text(
            f"Please enter the threshold for {label} between {min_val}{unit} and {max_val}{unit}, or use the suggested value:",
            reply_markup=markup_option
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(f"Please enter the threshold for {label} between {min_val}{unit} and {max_val}{unit}, or use the suggested value:",
            reply_markup=markup_option
        )
    return SET_THRESHOLDS

async def handle_threshold_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stage_of_set = user_data[user_id]['threshold_stage']
    d_thresholds = context.application.bot_data["default_thresholds"]

    # Get the value from button or text
    if update.callback_query:
        query = update.callback_query
        value_str = query.data
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
    else:
        value_str = update.message.text.strip()
    # Convert to int
    try:
        value = int(value_str)
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return SET_THRESHOLDS
    
    min_val = d_thresholds[stage_of_set]["min"]
    max_val = d_thresholds[stage_of_set]["max"]
    suggested_val = d_thresholds[stage_of_set]["suggested"]
    unit = d_thresholds[stage_of_set]["unit"]

    print (" >> Stage of set:", stage_of_set, "you arrived to the comparison of inserted value and min and max")

    if not (min_val <= value <= max_val):
        await update.message.reply_text(f"The value must be between {min_val}{unit} and {max_val}{unit}. Please try again or choose the recommended value.",
                                        reply_markup=await build_suggestion_keyboard(suggested_val, include_back=False)
        )
        return SET_THRESHOLDS
    
    user_data[user_id][f"{stage_of_set}_threshold"] = value
    print(" >> Value accepted:", value, "for stage:", stage_of_set, user_data[user_id][f"{stage_of_set}_threshold"])

    # Move to the next threshold
    if stage_of_set == 'temperature':
        user_data[user_id]['threshold_stage'] = 'humidity'
        return await ask_objective_threshold(update, context)
    elif stage_of_set == 'humidity':
        user_data[user_id]['threshold_stage'] = 'light'
        return await ask_objective_threshold(update, context)
    elif stage_of_set == 'light':
        text_shown = (
            f"✔ Thresholds configured:\n"
            f"🌡 Temperature: {user_data[user_id]['temperature_threshold']}{d_thresholds['temperature']['unit']}\n"
            f"💧 Humidity: {user_data[user_id]['humidity_threshold']}{d_thresholds['humidity']['unit']}\n"
            f"💡 Light: {user_data[user_id]['light_threshold']}{d_thresholds['light']['unit']}\n"
            "Please wait while the request is being processed. Thank you!"
        )
        if update.message:
            await update.message.reply_text(text_shown)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text_shown)

        # If creating a new greenhouse and area for the first time
        if user_data[user_id].get('new_gh_id') is not None: #so add a new greenhouse with area
            print(">> Creating the first greenhouse and area after thresholds")
            return await handle_create_first_a(update, context)
        # If creating a new area in an existing greenhouse
        elif user_data[user_id].get('gh_to_manage') is not None: # so add a new area
            # Get the thresholds from user_data
            await add_area_confirm(update, context)
        else:
            print(">> Internal error: issues between return functions")
    else:
        await update.message.reply_text("Internal error. Unrecognized stage. If the issue persists, contact support. Goodbye.")
        return ConversationHandler.END

async def add_area_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> You entered add_area_end_phase")
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']
    new_id = user_data[user_id]['new_area_id']
    plant_type = user_data[user_id]['plant_type']
    # Get the thresholds from user_data
    temperature_threshold = user_data[user_id]['temperature_threshold']
    humidity_threshold = user_data[user_id]['humidity_threshold']
    light_threshold = user_data[user_id]['light_threshold']
    print(">> Creating a new area in an existing greenhouse after thresholds")
    if await create_area(catalog_url, greenhouse_id, new_id, plant_type, temperature_threshold, humidity_threshold, light_threshold):
        # Remove the thresholds from user_data
        del user_data[user_id]['temperature_threshold']
        del user_data[user_id]['humidity_threshold']
        del user_data[user_id]['light_threshold']
        #NOT NEEDED IF THE BACK TO MAIN MENU DELETES THE ENTIRE user_data
        text_shown = f"Area successfully created! ID: {user_data[user_id]['new_area_id']}.\nIt contains plants of type: {plant_type}.\nReturn to the main menu."
        if update.message:
            await update.message.reply_text(text_shown, reply_markup=back_to_MM)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text_shown, reply_markup=back_to_MM)
        return FINAL_STAGE
    else:
        await update.message.reply_text("Error creating the area. Please try again.",
                                        reply_markup=(end_markup))
        return FINAL_STAGE

async def handle_create_first_a(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> Entró a handle_create_first_a")
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    gh_id = user_data[user_id]['new_gh_id']
    plant_type = user_data[user_id]['plant_type']
    # Get the thresholds from user_data
    temperature_threshold = user_data[user_id]['temperature_threshold']
    humidity_threshold = user_data[user_id]['humidity_threshold']
    light_threshold = user_data[user_id]['light_threshold']

    # Call the function to create the greenhouse and the area
    success = await create_greenhouse_and_area(catalog_url, user_id, gh_id, plant_type, temperature_threshold, humidity_threshold, light_threshold)
    
    if success:
        del user_data[user_id]['new_gh_id']  # Remove the key from user_data
        await update.message.reply_text(f"Greenhouse successfully created! ID: {gh_id}.\nIts first area contains plants of type: {plant_type}.\n"
                                        "Return to the main menu.",
            reply_markup=back_to_MM
        )
        return MAIN_MENU
    else:
        await update.message.reply_text("Error creating the greenhouse. Please try again or contact support.",
                                        reply_markup=back_to_MM)
        return CREATE_A

######## Manage and Delete combined part ##########
### List and elect the GreenHouse to Manage/Delete
async def handle_input_gh_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> Entered to handle_input_gh_id")
    user_id = update.effective_user.id
    #user_data[user_id]['gh_to_delete'] = None #Either this line or not use a BACK button
    #user_data[user_id]['gh_to_manage'] = None #Either this line or not use a BACK button
    #Query answer
    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    await query.edit_message_reply_markup(reply_markup=None)
    user_data[user_id]['action'] = query.data

    if query.data == 'delete_greenhouse':
        cosa_fai = "delete"
    elif query.data == 'manage_greenhouses':
        cosa_fai = "manage"

    # List the user's greenhouses
    user_data[user_id]['their_greenhouses'] = await check_gh_ownership(user_id, context.bot_data['catalog_url'])
    # If the user has no greenhouses, send a message and return to the main menu
    if not user_data[user_id]['their_greenhouses']:
        await update.callback_query.message.reply_text(
            "You don't have any greenhouses. Please go back and create one first.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]])
        )
        return MAIN_MENU
    # List the user's greenhouses and ask for the ID
    gh_list = "\n".join(
        f"-> {gh['greenhouseID']} (created on {gh['creation_date']})"
        for gh in sorted(user_data[user_id]['their_greenhouses'], key=lambda x: int(x['greenhouseID']))
    )
    await update.callback_query.message.reply_text(
        f"Here are your greenhouses:\n{gh_list}\n\nPlease enter the ID of the greenhouse you want to {cosa_fai}:",
        reply_markup=(back_to_MM)
    )
    return HANDLING_GH_ID

async def handle_gh_id_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        print(">> Entered handle_gh_id_selection")
        user_id = update.effective_user.id

        id_selected = update.message.text.strip()
        # Verify if the ID is valid, numeric, and has a maximum of 5 digits
        if not (id_selected.isdigit() and len(id_selected) < 5):
            del id_selected  # Is this necessary?
            await update.message.reply_text(
                "Invalid ID. It must be numeric and have a maximum of 5 digits. Please try again.",
                reply_markup=(back_to_MM)
            )
            return HANDLING_GH_ID

        # Verify that the ID belongs to the user
        if not any(gh["greenhouseID"] == id_selected for gh in user_data[user_id]['their_greenhouses']):
            await update.message.reply_text(
                "This greenhouse does not exist or does not belong to you. Please choose from the list.",
                reply_markup=(back_to_MM)
            )
            return HANDLING_GH_ID

        action = user_data[user_id]['action']  # 'delete_greenhouse' or 'manage_greenhouses'

        # If the ID is valid and exists, save it in user_data
        if action == 'delete_greenhouse':
            user_data[user_id]['gh_to_delete'] = id_selected
            await update.message.reply_text(f"ID accepted! The greenhouse to delete is: {id_selected}.")
            await update.message.reply_text(
                f"Are you sure you want to delete the greenhouse with ID: {id_selected}?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("CONFIRM", callback_data='confirm_delete_gh')],
                    [InlineKeyboardButton("CANCEL", callback_data='cancel_delete_gh')]
                ])
            )
            return CONFIRM_X_GH

        elif action == 'manage_greenhouses':
            user_data[user_id]['gh_to_manage'] = id_selected
            await update.message.reply_text(f"You have chosen the greenhouse with ID: {id_selected}.")
            await update.message.reply_text(
                "What would you like to do?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("MANAGE AREAS", callback_data='gestion_areas')],
                    [InlineKeyboardButton("ADD AREAS", callback_data='agregar_areas')],
                    [InlineKeyboardButton("DELETE AREA", callback_data='eliminacion_area')],
                    [InlineKeyboardButton("STORICAL DATA", callback_data='storical_data_gh')],
                    [InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]
                ])
            )
            return MANAGE_GH

####### Deleting an GH section #######
### Delete Greenhouse
async def handle_delete_gh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_to_delete = user_data[user_id]['gh_to_delete']

    query = update.callback_query
    await query.answer()  # Always respond to the callback, even if empty
    decision = query.data  # YES OR NO
    await query.edit_message_reply_markup(reply_markup=None)

    # If the user confirms deletion
    if decision == 'confirm_delete_gh':
        print("Entered confirm_delete_gh decision")
        if await delete_entire_greenhouse(catalog_url, greenhouse_to_delete):
            await update.callback_query.message.reply_text(f"Greenhouse with ID: {greenhouse_to_delete} successfully deleted.")
            user_data[user_id]['their_greenhouses'] = [
                gh for gh in user_data[user_id]['their_greenhouses']
                if gh['greenhouseID'] != greenhouse_to_delete
            ]
            # Remove the greenhouse from the user's list
            del user_data[user_id]['gh_to_delete']  # Remove the key from user_data
            # Return to the main menu
            await update.callback_query.message.reply_text(
                "Return to the main menu...",
                reply_markup=back_to_MM
            )
            return MAIN_MENU
        else:
            await update.callback_query.message.reply_text("Error deleting the greenhouse. Please try again.",
                                                           reply_markup=(back_to_MM)
            )
            return CONFIRM_X_GH
    elif decision == 'cancel_delete_gh':
        await update.callback_query.message.reply_text("Deletion canceled.")
        del user_data[user_id]['gh_to_delete']
        # Return to the main menu
        await update.callback_query.message.reply_text(
            "Return to the main menu...",
            reply_markup=back_to_MM
        )
        return MAIN_MENU
    else:
        await update.callback_query.message.reply_text("Invalid option. Please try again. Goodbye.")
        return ConversationHandler.END

######## Managing Greenhouse section ########
### Manage Add area
async def handle_add_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']
    # user_data[user_id]['area_to_add'] = None  # Either this line or not use a BACK button

    # Send the message with the generated buttons
    print("Entered handle_add_area")
    await update.callback_query.message.reply_text(
        "Let's add an area!"
    )
    available_id = await next_area_id(catalog_url, greenhouse_id)

    if available_id == 0:
        await update.callback_query.message.reply_text("The greenhouse already has 4 areas. No more can be added. Please add a new greenhouse or delete an area of this one.")
        await update.callback_query.message.reply_text(
            "Please return to the main menu.",
            reply_markup=(back_to_MM)
        )
        return MAIN_MENU  # MANAGE_GH
    else:
        user_data[user_id]['new_area_id'] = available_id
        await update.callback_query.message.reply_text(f"The area to be addes will be the Number: {available_id}.\n Please enter the type of plant (max 30 characters):",
                                                       reply_markup=(back_to_MM)
                                                       )
        return WAIT_PLANT

### Manage Greenhouse
async def handle_manage_gh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']

    print(">> Entered handle_manage_gh")
    query = update.callback_query
    await query.answer()  # Always respond to the callback, even if empty
    action = query.data
    await query.edit_message_reply_markup(reply_markup=None)
    print(f">> Selected action: {action}")

    user_data[user_id]['area_managing_desired_action'] = action

    print(">> Saved in user data for area managing desired action: ", user_data[user_id]['area_managing_desired_action'])
    # Get the areas
    areas = await list_areas(catalog_url, greenhouse_id)

    text_1 = (
        f"These are the areas of the greenhouse with ID: {greenhouse_id}:\n" +
        "\n".join([f"{area[0]} - {area[1]}" for area in areas])
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
        #prompt = f"Select an area to intervene in greenhouse ID {greenhouse_id}:"
        await update.callback_query.message.reply_text(text_1)
        return await handle_storical_data_gh(update, context)
    elif action == 'gestion_areas':
        prompt = f"Manage the areas of the greenhouse ID {greenhouse_id}:"
    elif action == 'eliminacion_area':
        prompt = f"Choose an area to delete from the greenhouse ID {greenhouse_id}:"
    else:
        prompt = f"Areas of the greenhouse ID {greenhouse_id}:"

    # Edit the original message to show text + buttons
    await query.edit_message_text(
        text=text_1 + "\n \n" + prompt,
        reply_markup=InlineKeyboardMarkup(markup_areas)
    )
    return SHOWING_AVAILABLE_AREAS
    
async def checking_what_to_do_showed_areas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        print(">> Entered checking_what_to_do_showed_areas")

        query = update.callback_query
        await query.answer()  # Always respond to the callback even if empty
        await query.edit_message_reply_markup(reply_markup=None)
        id_to_do = query.data.split("_")[1]  # Splits decision in ["area", "area_id"] and takes the [1]=id
        user_data[user_id]['area_to_do'] = id_to_do

        next_step = user_data[user_id]['area_managing_desired_action']

        # If the user chooses to manage areas
        if next_step == 'gestion_areas':
            await update.callback_query.message.reply_text(
                f"🔍 *Monitoring & Control Menu*\n"
                f"You have selected the area with ID: {id_to_do}. Choose what to do next:\n"
                f"_(You can return or exit below)_\n"
                f"1️⃣ *Sensors*\n"
                f"2️⃣ *Actuators*\n",
                parse_mode='Markdown',
                reply_markup=A_Mg_markup
            )
            print (">> You are in line 729/759 checking what to do and to do is manage area.. waiting instruction")
            return WAIT_AREA_INSTRUCTION

        # If the user chooses to delete areas
        elif next_step == 'eliminacion_area':
            user_data[user_id]['area_to_delete'] = id_to_do
            await update.callback_query.message.reply_text(
                f"Are you sure you want to delete the area with ID: {id_to_do}?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("CONFIRM", callback_data='confirm_delete_area')],
                    [InlineKeyboardButton("CANCEL", callback_data='cancel_delete_area')]
                ])
            )
            print(">> About to confirm elimination of area pre entering CONFIRM X A state..... 742")
            return CONFIRM_X_A

        else:
            await update.callback_query.message.reply_text("Invalid option. Please try again or contact support.")
            return ConversationHandler.END
        
async def handle_storical_data_gh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print( ">> Entered handle_storical_data_gh")
    show_text = (
        "📡 Follow the next link to see the data of the greenhouse that your plan has access to:\n"
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
    return FINAL_STAGE

async def handle_wait_new_a_plant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        catalog_url = context.bot_data['catalog_url']
        greenhouse_id = user_data[user_id]['gh_to_manage']
        new_id = user_data[user_id]['new_area_id']
        temperature_threshold = user_data[user_id]['temperature_threshold']
        humidity_threshold = user_data[user_id]['humidity_threshold']
        light_threshold = user_data[user_id]['light_threshold']

        # if update.callback_query:
        #     plant_type = user_data[user_id]['plant_type']
        # elif update.message:
        plant_type = update.message.text.strip()

        # Verify that the plant type does not exceed 30 characters
        if len(plant_type) > 30 or not plant_type.isalnum():
            await update.message.reply_text(
                "Error: Do not exceed 30 characters. Only letters and numbers are allowed. Please try again.",
                reply_markup=(back_to_MM)
            )
            del plant_type
            return ADD_A

        if await create_area(catalog_url, greenhouse_id, new_id, plant_type, temperature_threshold, humidity_threshold, light_threshold):
            await update.message.reply_text(
                f"Area successfully created! ID: {new_id}.\nIt contains plants of type: {plant_type}."
            )
        else:
            await update.message.reply_text("Error creating the area. Please try again.",
                                            reply_markup=(back_to_MM)
            )
            return ADD_A  # Handle this better if needed.....

        del user_data[user_id]['new_area_id']  # Remove the key from user_data
        # Return to the main menu
        await update.message.reply_text(
            "Return to the main menu.",
            reply_markup=back_to_MM
        )
        return MAIN_MENU

### Delete Area ## me falta pero lo de controlar si es la ultima area..........
async def handle_delete_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']

    # Check if the area to delete is the last one in the greenhouse
    areas = await list_areas(catalog_url, greenhouse_id)
    # If it is the last area, ask for confirmation to delete the greenhouse as well
    if len(areas) == 1:
        await update.callback_query.message.reply_text(
            "This is the last area in the greenhouse. Are you sure you want to delete it? The greenhouse will also be deleted.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("CONFIRM BOTH", callback_data='confirm_delete_both')],
                [InlineKeyboardButton("CANCEL", callback_data='cancel_delete_both')]
            ])
        )
        return CONFIRM_X_BOTH
    else:
        return await confirm_delete_area(update, context)
    
async def confirm_delete_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    greenhouse_id = user_data[user_id]['gh_to_manage']
    area_X = user_data[user_id]['area_to_delete']
    
    query = update.callback_query
    await query.answer()  # Always respond to the callback even if empty
    decision = query.data
    await query.edit_message_reply_markup(reply_markup=None)
    # If the user confirms
    if decision == 'confirm_delete_area':
        if await delete_area(catalog_url, greenhouse_id, area_X):
            await update.callback_query.message.reply_text(f"Area with ID: {area_X} successfully deleted.",
                                                           reply_markup=end_markup)
            # Return to the main menu
            return FINAL_STAGE
        else:
            await update.callback_query.message.reply_text("Error deleting the area. Please try again.")
            return CONFIRM_X_A
    elif decision == 'cancel_delete_area':
        await update.callback_query.message.reply_text("Deletion canceled.")
        del user_data[user_id]['area_to_delete']
        # Return to the main menu
        await update.callback_query.message.reply_text(
            "Return to the main menu.",
            reply_markup=end_markup
        )
        return FINAL_STAGE
    else:
        await update.callback_query.message.reply_text(f"Unexpected error. Please try again.\n If it persists, contact support. Goodbye!")
        return ConversationHandler.END

async def confirm_delete_both(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    greenhouse_id = user_data[user_id]['gh_to_manage']
    area_X = user_data[user_id]['area_to_delete']
    
    query = update.callback_query
    await query.answer()  # Always respond to the callback even if empty
    decision = query.data
    await query.edit_message_reply_markup(reply_markup=None)

    # If the user confirms
    if decision == 'confirm_delete_both':
        if await delete_entire_greenhouse(catalog_url, greenhouse_id):
            await update.callback_query.message.reply_text(f"Greenhouse with ID: {greenhouse_id} and area with ID: {area_X} successfully deleted.")
            if any(gh['greenhouseID'] == greenhouse_id for gh in user_data[user_id]['their_greenhouses']):
                remove_greenhouse(user_id, greenhouse_id)
            else:
                print(f"Warning: Greenhouse {greenhouse_id} was not in the list for user {user_id}")
            del user_data[user_id]['area_to_delete']  # Remove the key from user_data
            # Return to the main menu
            await update.callback_query.message.reply_text(
                "Return to the main menu. Goodbye.",
                reply_markup=end_markup
            )
            return FINAL_STAGE
        else:
            await update.callback_query.message.reply_text("Error deleting the greenhouse. Please try again.")
            return CONFIRM_X_BOTH
    elif decision == 'cancel_delete_both':
        await update.callback_query.message.reply_text("Deletion canceled.")
        del user_data[user_id]['area_to_delete']
        # Return to the main menu
        await update.callback_query.message.reply_text(
            "Return to the main menu.",
            reply_markup=end_markup
        )
        return FINAL_STAGE  # OR MANAGE_GH IN THE FUTURE
    else:
        await update.callback_query.message.reply_text("Critical error. Please try again. Goodbye.")
        return ConversationHandler.END


# async def handle_actions_invernadero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     # Aquí puedes manejar la lógica para las acciones del invernadero
#     pass

############################## Callback Query Handlers ##############################
async def handle_bye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data[user_id] = {}
    bye_msg = "Goodbye! See you next time. Thank you for choosing us!"
    if update.message:
        await update.message.reply_text(bye_msg)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(bye_msg)
    print(f">> User {user_id} ended the conversation.")
    return ConversationHandler.END

async def handle_back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id in user_data:
        user_data[user_id] = {}

    query = update.callback_query
    if query:
        await query.answer()
        print( "arrivato a 894, back to main menu")
        # Remove the previous buttons from that message
        await query.edit_message_reply_markup(reply_markup=None)
        # Send a new message with text and new buttons
        await query.message.reply_text(
            "Welcome to the Main Menu.\n What would you like to do?",
            reply_markup=main_menu_keyboard
        )
    else:
        # If not a callback, just send the new message with buttons
        print( "arrivato a 904, back to main menu")
        await update.message.reply_text(
            "Welcome to the Main Menu.\n What would you like to do?",
            reply_markup=main_menu_keyboard
        )
    return MAIN_MENU

# async def handle_back_to_create_gh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     user_data[update.effective_user.id] = {} ### REVISAR
#     await update.message.reply_text("Regresando a la creación del invernadero...")
#     return CREATE_GH

async def handle_acciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Aquí puedes manejar la lógica para las acciones del invernadero
    await update.callback_query.message.reply_text("Funcionalidad no implementada todavía. FINALIZANDO")
    return ConversationHandler.END

async def handle_verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    greenhouse_id = user_data[user_id]['gh_to_manage']
    area_processing = user_data[user_id]['area_to_do']
    
    # Communicate with the catalog and retrieve the current values
    area = await get_area(catalog_url, greenhouse_id, area_processing)
    if area.status_code != 200:
        await update.callback_query.message.reply_text("Error retrieving area data. Please try again or contact support.",
                                                       reply_markup=end_markup
        )
        return FINAL_STAGE
    
    query = update.callback_query
    await query.answer()  # Always respond to the callback even if empty
    to_verify = query.data 

    if to_verify == 'check_temperature':
        variable = "temperature"
        current_value = area.get('currentTemperature', 'Unknown')
    elif to_verify == 'check_humidity':
        variable = "humidity"
        current_value = area.get('currentHumidity', 'Unknown')
    elif to_verify == 'check_luminosity':
        variable = "luminosity"
        current_value = area.get('currentLuminosity', 'Unknown')

    unit = area.get('unit', 'Unknown')

    await query.edit_message_reply_markup(reply_markup=None)
    await update.callback_query.message.reply_text(
            f"📟 The current {variable} in Area {area_processing} of greenhouse {greenhouse_id} is: {current_value}{unit}.\n",
            parse_mode="Markdown",
            reply_markup=A_Mg_markup
        )
    return WAIT_AREA_INSTRUCTION

async def handle_actuators_a(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    greenhouse_id = user_data[user_id]['gh_to_manage']
    area_processing = user_data[user_id]['area_to_do']

    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    actuator_selection = query.data
    user_data[user_id]['actuator_selection'] = actuator_selection
    await query.edit_message_reply_markup(reply_markup=None)

    if actuator_selection == 'manage_pump':
        macchinetta = "pump"
    elif actuator_selection == 'manage_light':
        macchinetta = "light"
    elif actuator_selection == 'manage_fan':
        macchinetta = "ventilation system"
    
    await update.callback_query.message.reply_text(
        f"Do you want to turn on or off the {macchinetta} in Area {area_processing} of Greenhouse {greenhouse_id}?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("ON", callback_data='on')],
            [InlineKeyboardButton("OFF", callback_data='off')],
            [InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]
        ])
    )
    return WAIT_ACTUATOR_STATE

async def handle_actuator_state(update: Update, context: ContextTypes.DEFAULT_TYPE, publisherMQTT) -> int:
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    greenhouse_id = user_data[user_id]['gh_to_manage']
    area_processing = user_data[user_id]['area_to_do']
    actuator_selection = user_data[user_id]['actuator_selection']

    query = update.callback_query
    await query.edit_message_reply_markup(reply_markup=None)
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    to_set_on_off = query.data  # ON or OFF
    #user_data[user_id]['action_wanted'] = to_set_on_off    #Not needed?

    #Check if the actuator is already on or off
    state_a = await check_actuator_state(catalog_url, greenhouse_id, area_processing, actuator_selection)
    user_data[user_id]['actuator_state'] = state_a

    print(">> Actuator selection: ", actuator_selection)
    print( ">> To_set_on_off: ", to_set_on_off)
    print (">> Actuator state line 1033: ", state_a)

    if actuator_selection == 'manage_pump':
        oki = await set_actuator(update, greenhouse_id, area_processing, "pumpActuation",to_set_on_off, publisherMQTT)
    elif actuator_selection == 'manage_light':
        oki = await set_actuator(update, greenhouse_id, area_processing, "lightActuation", to_set_on_off, publisherMQTT)
    elif actuator_selection == 'manage_fan':
        oki = await set_actuator(update, greenhouse_id, area_processing, "ventilationActuation", to_set_on_off, publisherMQTT)
    else:
        await update.callback_query.message.reply_text("Invalid actuator. Please try again.",
                                                       reply_markup=end_markup
        )
        return FINAL_STAGE
    
    #check if to_set_on_off is 1 or 0 and convert it to on or off for showing to the user
    if to_set_on_off == 1:
        to_set_on_off_show = "ON"
    elif to_set_on_off == 0:
        to_set_on_off_show = "OFF"

    # Check the response from the MQTT publish
    if oki["status_ok"] == 200:
        await update.callback_query.message.reply_text(
            f"Actuator {actuator_selection} in Area {area_processing} of Greenhouse {greenhouse_id} is now: {to_set_on_off_show}",
            reply_markup=end_markup
        )
    else:
        await update.callback_query.message.reply_text(f"Error sending MQTT command: {oki.get('error', 'unknown')}. Contact Support.",
                                                       reply_markup=end_markup
)
    return FINAL_STAGE

async def check_actuator_state(catalog_url, greenhouse_id, area_processing, actuator_type):
    try: #greenhouse1/areas/1  #greenhouse1/areas/1 
        response = await get_area(catalog_url, greenhouse_id, area_processing)
        if response.status_code == 200:
            area = response.json()
            #get the actuator state
            if actuator_type == "pumpActuation":
                state = area['pump']
            elif actuator_type == "lightActuation":
                state = area['light']
            elif actuator_type == "ventilationActuation":
                state = area['ventilation']
            else:
                print("Invalid actuator type")
                return None
            return state
        else:
            print(f"Error in the request: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error while retrieving area details: {e}. Contact support.")
        return None

async def set_actuator(update, greenhouse_id, area_processing, actuator_type, to_set_on_off, publisherMQTT):
    user_id = update.effective_user.id
    state_previous = user_data[user_id]['actuator_state']
    action_wanted = to_set_on_off


    print(f"DEBUG - user_id: {user_id}")
    print(f"DEBUG - state_previous (actuator_state): {state_previous} (type: {type(state_previous)})")
    print(f"DEBUG - action_wanted (to_set_on_off): {action_wanted} (type: {type(action_wanted)})")


    if normalize_state_to_int(state_previous) == normalize_state_to_int(action_wanted):
            await update.callback_query.message.reply_text(
                f"The actuator is already {normalize_state_to_str(state_previous)}.\n No changes made. Return to Main Menu.",
                reply_markup=back_to_MM
            )
            return FINAL_STAGE #OR MAIN MENU
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
                await update.callback_query.message.reply_text(
                    "Invalid actuator type. Please try again. if the problem persists, contact support.",
                    reply_markup=end_markup
                )
                return FINAL_STAGE
            
            #it uses MQTT to send the command to the actuators
    #It should publish to the topic                 "pumpActuation": f"greenhouse{int(greenhouse_id)}/area{area_id}/actuation/pump",
                #"lightActuation": f"greenhouse{int(greenhouse_id)}/area{area_id}/actuation/light",
                #"ventilationActuation": f"greenhouse{int(greenhouse_id)}/area{area_id}/actuation/ventilation",
        # and the payload should be {"state": 1} or {"state": 0} ## VERIFYYYYY

            # Simulate sending the actuation command (replace with actual MQTT or API call)
            #payload = {"state": to_set_on_off}

            if actuator_type == "lightActuation":
                payload = action_wanted.lower()  # 'on' o 'off'
            else:
                # Para otros, enviamos entero 0 o 1
                payload = normalize_state_to_int(action_wanted)  # int 0 o 1

            response = publisherMQTT.publish(topic, payload)


            if response.rc == 0:
                print(f"Actuator command sent to {topic} with payload {payload}. Response: {response.rc}")
                return {"status_ok": True, "rc": response.rc}
            else:
                print("Error al publicar mensaje MQTT")
                return {"status_ok": False, "rc": response.rc}
        except Exception as e:
            print(f"Error while setting actuator state: {e}")
            await update.callback_query.message.reply_text(
                "An error occurred while setting the actuator state. Please try again. If the problem persists, contact support.",
                reply_markup=end_markup
            )
            return FINAL_STAGE

    #state_a is 0 or 1 for "pump or ventialation" and on or off for light.

def normalize_state_to_int(value):
    if isinstance(value, str):
        value = value.strip().lower()
        if value == "on":
            return 1
        if value == "off":
            return 0
    return int(value)

def normalize_state_to_str(value):
    if str(value) == "1":
        return "ON"
    else:
        return "OFF"


async def timeout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message:
        del user_data[user_id]
        await update.message.reply_text("⏳ Timeout. The conversation was closed due to inactivity.")
    elif update.callback_query:
        del user_data[user_id]
        await update.callback_query.answer("⏳ Timeout.")
        await update.callback_query.message.reply_text("⏳ Timeout. The conversation was closed due to inactivity.")
    return ConversationHandler.END

############################# CLASSES #############################
class BotMain:
    def __init__(self, config):
        self.token = config['telegram_token']
        self.catalog_url = config['catalog_url']
        self.default_thresholds = config['default_thresholds']

        self.application = Application.builder().token(self.token).build()
        self.application.bot_data['catalog_url'] = self.catalog_url
        self.application.bot_data['default_thresholds'] = self.default_thresholds

        # Aquí agregarías handlers, comandos, conversation handler, etc.
        #self.notifier = TelegramAlertNotifier(application, self.catalog_url)
        #self.mqtt_client = MyMQTTforBOT("BotAlertListener", self.mqtt_broker, self.mqtt_port, self.notifier)

        # # Mapa greenhouse_id → user_id
        # self.greenhouse_user_map = {}

        # # Instancio el AlertNotifier con acceso a application y el mapa
        # self.alert_notifier = AlertNotifier(self.application, self.catalog_url, self.greenhouse_user_map)

        # # MQTT setup
        # self.mqtt = MyMQTT("BotClient", self.config["broker_ip"], self.config["broker_port"], self.alert_notifier)
        # self.mqtt.start()
        # self.mqtt.mySubscribe("your/alert/topic")

        conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, start)],
            states={
                MAIN_MENU: [
                    CallbackQueryHandler(handle_wait_new_gh_id , pattern='^add_greenhouse$'),
                    CallbackQueryHandler(handle_input_gh_id, pattern='^manage_greenhouses$'),
                    CallbackQueryHandler(handle_input_gh_id, pattern='^delete_greenhouse$'),
                    CallbackQueryHandler(handle_bye, pattern='^bye$'),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='^back_to_main_menu$'),
                ],
                WAIT_NEW_GH_ID: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_check_gh_id_and_wait_new_gh_plant),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                WAIT_PLANT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plant_set_start_thresholds),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CHECK_FIRST_THRESHOLD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,handle_threshold_input ),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                SET_THRESHOLDS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_threshold_input),
                    CallbackQueryHandler(handle_threshold_input, pattern=r"^\d+$"),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CREATE_A: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_create_first_a), ########## CONTROL
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                INPUT_GH_ID: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_gh_id),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                HANDLING_GH_ID: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gh_id_selection),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CONFIRM_X_GH: [
                    CallbackQueryHandler(handle_delete_gh, pattern='confirm_delete_gh'),
                    CallbackQueryHandler(handle_delete_gh, pattern='cancel_delete_gh'),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                MANAGE_GH: [
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                    CallbackQueryHandler(handle_add_area, pattern='agregar_areas'),
                    CallbackQueryHandler(handle_manage_gh), #Rest of the options
                ],
                SHOWING_AVAILABLE_AREAS: [
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'), #first checks if this happened
                    CallbackQueryHandler(checking_what_to_do_showed_areas),
                ],                 
                ADD_A : [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wait_new_a_plant),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CONFIRM_X_A: [
                    CallbackQueryHandler(handle_delete_area, pattern='confirm_delete_area'),
                    CallbackQueryHandler(handle_delete_area, pattern='cancel_delete_area'),
                ],        
                WAIT_AREA_INSTRUCTION
                : [
                    CallbackQueryHandler(handle_acciones, pattern='acciones_invernadero'),
                    CallbackQueryHandler(handle_verify, pattern='check_humidity'),
                    CallbackQueryHandler(handle_verify, pattern='check_temperature'),
                    CallbackQueryHandler(handle_verify, pattern='check_luminosity'),
                    CallbackQueryHandler(handle_actuators_a, pattern='manage_pump'),
                    CallbackQueryHandler(handle_actuators_a, pattern='manage_fan'),
                    CallbackQueryHandler(handle_actuators_a, pattern='manage_light'),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                    CallbackQueryHandler(handle_bye, pattern='bye'),
                ],
                WAIT_ACTUATOR_STATE: [
                    CallbackQueryHandler(partial(handle_actuator_state, publisherMQTT=MQTTBuddy), pattern='on'),
                    CallbackQueryHandler(partial(handle_actuator_state, publisherMQTT=MQTTBuddy), pattern='off'),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CONFIRM_X_BOTH: [
                    CallbackQueryHandler(confirm_delete_both, pattern='confirm_delete_both'),
                    CallbackQueryHandler(confirm_delete_both, pattern='cancel_delete_both'),
                ],
                FINAL_STAGE: [
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                    CallbackQueryHandler(handle_bye, pattern='bye'),
                ],
                ConversationHandler.TIMEOUT: [
                    MessageHandler(filters.ALL, timeout_callback),
                    CallbackQueryHandler(timeout_callback)
                ]
            },
            fallbacks=[CommandHandler('start', start)],
            conversation_timeout=180 # Timeout: 3 minutes
        )

        self.application.add_handler(conv_handler)
    def run(self):
        self.application.run_polling()

if __name__ == "__main__":
    config = load_config()
    DEFAULT_THRESHOLDS = config["default_thresholds"]
    #instance of MyMQTT
    MQTTBuddy = MyMQTTforBOT.MyMQTT(2903, config.get("mqtt_broker"), config.get("mqtt_port"))
    bot = BotMain(config)
    bot.run()

