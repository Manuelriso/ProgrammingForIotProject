import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from datetime import datetime
import MyMQTTforBOT as MyMQTTforBOT
from functools import partial #for inserting parameters in callbacks

# Estados del árbol de conversación
# MAIN_MENU, CREATE_GH, CREATE_A, INPUT_GH_ID, MANAGE_GH, MANAGE_AREA, CONFIRM_X_GH, ADD_A, DELETE_A, CONFIRM_X_A,  CONFIRM_X_BOTH = range(11)
MAIN_MENU, WAIT_NEW_GH_ID, WAIT_NEW_GH_PLANT, CREATE_A, INPUT_GH_ID, HANDLING_GH_ID, CONFIRM_X_GH, MANAGE_GH, SHOWING_AVAILABLE_AREAS, CONFIRM_X_A, CONFIRM_X_BOTH, ADD_A, WAIT_AREA_INSTRUCTION, WAIT_ACTUATOR_STATE, FINAL_STAGE = range(15)

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

A_Mg_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("VERIFY HUMIDITY", callback_data='check_humidity')],
            [InlineKeyboardButton("VERIFY TEMPERATURE", callback_data='check_temperature')],
            [InlineKeyboardButton("VERIFY LUMINOSITY", callback_data='check_luminosity')],
            [InlineKeyboardButton("MANAGE PUMP", callback_data='manage_pump')],
            [InlineKeyboardButton("MANAGE FAN", callback_data='manage_fan')],
            [InlineKeyboardButton("MANAGE LIGHT", callback_data='manage_light')],
            [InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]
        ]) 

######################### AUXILIARY FUNCTIONS #########################
### Verify if the greenhouse ID exists in the database
import requests

async def check_gh_id_exists(catalog_url, greenhouse_id) -> bool:
    try:
        print("Before GET request")
        response = requests.get(f"{catalog_url}greenhouses", timeout=5)  # Timeout para no bloquear mucho
        print("After GET request")
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


# async def check_gh_id_exists(catalog_url, greenhouse_id) -> bool:
#     try:
#         response = requests.get(f"{catalog_url}greenhouses")
#         if response.status_code == 200:
#             greenhouses = response.json().get("greenhouses", [])
#             print("IDs in catalog:", [gh['greenhouseID'] for gh in greenhouses])
#             print("Checking ID:", greenhouse_id)
#             # Comparar convertidos a enteros
#             result = any(int(gh['greenhouseID']) == int(greenhouse_id) for gh in greenhouses)
#             print("Exists:", result)
#             #return any(int(gh['greenhouseID']) == int(greenhouse_id) for gh in greenhouses)
#             return result
#         return False  # Cambiado a False, ya que no se encontró el ID y no hubo error
#     except requests.exceptions.RequestException:
#         return True  # Mantener True para manejar errores de conexión

### Create a new greenhouse in the database with first area
async def create_greenhouse_and_area(catalog_url, user_id, greenhouse_id, plant_type) -> bool:
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
                "humidityThreshold": 80,  # This should be a variable
                "temperatureThreshold": 21,  # This should be a variable
                "luminosityThreshold": 60,  # This should be a variable
                "plants": plant_type,
                "temperatureDataTopic": f"greenhouse{int(greenhouse_id)}/area1/temperature",
                "humidityDataTopic": f"greenhouse{int(greenhouse_id)}/area1/humidity",
                "luminosityDataTopic": f"greenhouse{int(greenhouse_id)}/area1/luminosity",
                "motionTopic": f"greenhouse{int(greenhouse_id)}/area1/motion",
                "motionDetected": 0,
                "pumpActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/pump",
                "lightActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/light",
                "ventilationActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/ventilation",
                "pump": 0,
                "light": "off",
                "ventilation": 0
            }
            ]
        }
        # Log the POST request for debugging purposes
        print(f"Sending POST request to: {catalog_url}greenhouse")
        response = requests.post(f"{catalog_url}greenhouse", json=new_greenhouse)  # POST request ###singular
        print(f"Status code: {response.status_code}")
        #print(f"Response text: {response.text}")

        if response.status_code == 201:
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False

### Create a new area in the database
async def create_area(catalog_url, greenhouse_id, area_id, plant_type) -> bool:
    try:
        # Aquí debes definir la estructura del área que deseas crear
        new_area = {
            "ID": area_id,
            "humidityThreshold": 80,  ########## THIS SHOULD BE A VARIABLE
            "temperatureThreshold": 21,  ######### THIS SHOULD BE A VARIABLE
            "luminosityThreshold": 60,  ############ THIS SHOULD BE A VARIABLE
            "plants": plant_type,
            "temperatureDataTopic": f"greenhouse{int(greenhouse_id)}/area{area_id}/temperature",
            "humidityDataTopic": f"greenhouse{int(greenhouse_id)}/area{area_id}/humidity",
            "luminosityDataTopic": f"greenhouse{int(greenhouse_id)}/area{area_id}/luminosity",
            "motionTopic": f"greenhouse{int(greenhouse_id)}/area{area_id}/motion",
            "motionDetected": 0,
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
            # Si ya hay 4 áreas, no se puede agregar más
            if len(area_ids) >= 4:
                return 0
            # Buscar el primer ID libre del 1 al 4
            for i in range(1, 5):
                if i not in area_ids:
                    return i  # Retornar el primer ID disponible
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
    
### Delete an area inside a greenhouse  (maybe unify with delete entire and work with callback to know what)
async def delete_area(catalog_url, greenhouse_id, area_id) -> bool:
    try:
        response = requests.delete(f"{catalog_url}greenhouse{greenhouse_id}/area/{area_id}") #####greenhouse1/area/1 
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
            print(f"Server response: {response.text}")  # Additional debug
            if response.status_code == 200:
                data = response.json()  # Get the response body
                areas = data.get("areas", [])  # Ensure 'areas' exists and is a list
                print(f"Obtained areas: {areas}")  # Show the areas retrieved from the server
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

def remove_greenhouse(user_id, greenhouse_id): #only from internal temporal list
    user_data[user_id]['their_greenhouses'] = [
        gh for gh in user_data[user_id]['their_greenhouses']
        if gh['greenhouseID'] != greenhouse_id
    ]

############################### CONVERSATION STATES ###############################
# Inicio del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data[user_id] = {}
    await update.message.reply_text('GREENHOUSE ALLA TERRONE', reply_markup=ReplyKeyboardRemove())
    # Reply keyboard in the text area
    await update.message.reply_text(f"Welcome! Your ID is {user_id}. What would you like to do?", reply_markup=main_menu_keyboard)
    user_data[user_id]['their_greenhouses'] = await check_gh_ownership(user_id, context.bot_data['catalog_url'])
    return MAIN_MENU

####### CREATION PART ##########
###Manejo de ID de adición/creación de invernadero
async def handle_wait_new_gh_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> You entered a handle_wait_new_gh_id")
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    # Back button
    back_button = InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')
    markup = InlineKeyboardMarkup([[back_button]])

  # Always respond to the callback, even if empty
    await update.callback_query.message.reply_text(
        "Enter a numeric ID (max 5 digits), or press BACK.",
        reply_markup=markup
    )
    # Esperar la respuesta del usuario
    return WAIT_NEW_GH_ID

async def handle_check_gh_id_and_wait_new_gh_plant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> You etnered to handle_check_gh_id_and_wait_new_gh_plant")
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']

    gh_id = update.message.text.strip()
    
    if not (gh_id.isdigit() and len(gh_id) < 5):
        await update.message.reply_text("Invalid ID. It must be numeric and have maximal 5 digits. Try again.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]]) 
        )
        return WAIT_NEW_GH_ID
    # Verifica si el ID ya existe en la base de datos
    if await check_gh_id_exists(catalog_url, gh_id):
        await update.message.reply_text("This ID is already in use. Please choose another one.",
        reply_markup=back_to_MM                      
        )
        # El bot seguirá esperando automáticamente en este estado (CREATE_GH) debido a la estructura del ConversationHandler.
        # No necesitas agregar código adicional aquí para manejar el ingreso de texto del usuario.
        # El estado CREATE_GH ya está configurado para manejar mensajes de texto y volver a llamar a `handle_create_gh`.
        return WAIT_NEW_GH_ID
        # If the ID is valid and does not exist, save it in user_data
    user_data[user_id]['new_gh_id'] = gh_id
    await update.message.reply_text(f"ID accepted! Your greenhouse will have the ID: {gh_id}. Let's design its first area!",
        reply_markup=(back_to_MM)
        )
    await update.message.reply_text(
            "Please enter the type of plant for the area (max 30 characters):",
            reply_markup=(back_to_MM)
        )
    return CREATE_A

### Create the first area of the greenhouse
async def handle_create_first_a(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> Entró a handle_create_first_a")
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    gh_id = user_data[user_id]['new_gh_id']

    plant_type = update.message.text.strip()
    
    # Verify that the plant type does not exceed 30 characters
    if (len(plant_type) > 30 or not plant_type.isalnum()):
        await update.message.reply_text("Error: Do not exceed 30 characters, only letters and numbers are allowed. Please try again.",
        reply_markup=(back_to_MM)
        )
        return CREATE_A
    
    # Call the function to create the greenhouse and the area
    success = await create_greenhouse_and_area(catalog_url, user_id, gh_id, plant_type)
    
    if success:
        await update.message.reply_text(f"Greenhouse successfully created! ID: {gh_id}.\nIts first area contains plants of type: {plant_type}.")
        del user_data[user_id]['new_gh_id']  # Remove the key from user_data
        # Return to the main menu
        await update.message.reply_text(
            "Greenhouse successfully created. Return to the main menu.",
            reply_markup=back_to_MM
        )
        return MAIN_MENU
    else:
        await update.message.reply_text("Error creating the greenhouse. Please try again.")
        return CREATE_A

######## Manage and Delete combined part ##########
### List and elect the GreenHouse to Manage/Delete
async def handle_input_gh_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> Entró a handle_input_gh_id")
    user_id = update.effective_user.id
    #user_data[user_id]['gh_to_delete'] = None #Either this line or not use a BACK button
    #user_data[user_id]['gh_to_manage'] = None #Either this line or not use a BACK button
    #Query answer
    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    await query.edit_message_reply_markup(reply_markup=None)

    user_data[user_id]['action'] = query.data
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
        f"Here are your greenhouses:\n{gh_list}\n\nPlease enter the ID of the greenhouse you want to manage or delete:",
        reply_markup=(back_to_MM)
    )
    # Wait for the user's response
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
            await update.message.reply_text(f"ID accepted! The greenhouse to manage is: {id_selected}.")
            await update.message.reply_text(
                f"You have selected the greenhouse with ID: {id_selected}. What would you like to do?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("MANAGE AREAS", callback_data='gestion_areas')],
                    [InlineKeyboardButton("ADD AREAS", callback_data='agregar_areas')],
                    [InlineKeyboardButton("DELETE AREA", callback_data='eliminacion_area')],
                    [InlineKeyboardButton("GREENHOUSE ACTIONS", callback_data='acciones_invernadero')],
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
        "Let's add an area:",
        reply_markup=(back_to_MM)
    )
    available_id = await next_area_id(catalog_url, greenhouse_id)

    if available_id == 0:
        await update.callback_query.message.reply_text("The greenhouse already has 4 areas. No more can be added. Please create a new greenhouse.")
        await update.callback_query.message.reply_text(
            "Please return to the main menu.",
            reply_markup=(back_to_MM)
        )
        return MAIN_MENU  # MANAGE_GH
    else:
        user_data[user_id]['new_area_id'] = available_id
        await update.callback_query.message.reply_text(f"The ID of the area to be added is: {available_id}. Please enter the type of plant (max 30 characters):",
                                                       reply_markup=(back_to_MM)
                                                       )
        return ADD_A

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

    await update.callback_query.message.reply_text(
        f"These are the areas of the greenhouse with ID: {greenhouse_id}."
    )
    
    # Get the areas
    areas = await list_areas(catalog_url, greenhouse_id)

    # Build markup for areas (buttons)
    buttons_areas = [
        InlineKeyboardButton(f"{area[0]} - {area[1]}", callback_data=f"area_{area[0]}")
        for area in areas
    ]
    markup_areas = [buttons_areas[i:i + 2] for i in range(0, len(buttons_areas), 2)]
    markup_areas.append([InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')])

    # Text based on the action
    if action == 'gestion_areas':
        prompt = f"Manage the areas of the greenhouse ID {greenhouse_id}:"
    elif action == 'eliminacion_area':
        prompt = f"Choose an area to delete from the greenhouse ID {greenhouse_id}:"
    elif action == 'acciones_invernadero':
        prompt = f"Select an area to intervene in greenhouse ID {greenhouse_id}:"
    else:
        prompt = f"Areas of the greenhouse ID {greenhouse_id}:"

    # Edit the original message to show text + buttons
    await query.edit_message_text(
        text=prompt,
        reply_markup=InlineKeyboardMarkup(markup_areas)
    )
    return SHOWING_AVAILABLE_AREAS
    
async def checking_what_to_do_showed_areas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        catalog_url = context.bot_data['catalog_url']
        greenhouse_id = user_data[user_id]['gh_to_manage']

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
                f"You have selected the area with ID: {user_data[user_id]['area_to_do']}. Choose what to do next:",
                reply_markup=A_Mg_markup
            )
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
            return CONFIRM_X_A

        elif next_step == 'acciones_invernadero':
            user_data[user_id]['area_to_intervene'] = id_to_do
            # Functionality not implemented yet
            await update.callback_query.message.reply_text("This functionality is not implemented yet. Goodbye.")
            return ConversationHandler.END

        else:
            await update.callback_query.message.reply_text("Invalid option. Please try again or contact support.")
            return ConversationHandler.END

async def handle_wait_new_a_plant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        catalog_url = context.bot_data['catalog_url']
        greenhouse_id = user_data[user_id]['gh_to_manage']
        new_id = user_data[user_id]['new_area_id']

        plant_type = update.message.text.strip()
        # Verify that the plant type does not exceed 30 characters
        if len(plant_type) > 30 or not plant_type.isalnum():
            await update.message.reply_text(
                "Error: Do not exceed 30 characters. Only letters and numbers are allowed. Please try again.",
                reply_markup=(back_to_MM)
            )
            del plant_type
            return ADD_A

        if await create_area(catalog_url, greenhouse_id, new_id, plant_type):
            await update.message.reply_text(
                f"Area successfully created! ID: {user_data[user_id]['new_area_id']}.\nIt contains plants of type: {plant_type}."
            )
        else:
            await update.message.reply_text("Error creating the area. Please try again.")
            return ADD_A  # Handle this better if needed.

        del user_data[user_id]['new_area_id']  # Remove the key from user_data
        # Return to the main menu
        await update.message.reply_text(
            "Returning to the main menu.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]])
        )
        return MAIN_MENU

### Delete Area ## me falta pero lo de controlar si es la ultima area..........
async def handle_delete_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']
    area_X = user_data[user_id]['area_to_delete']

    # Verifica si el área a eliminar es la última del invernadero
    areas = await list_areas(catalog_url, greenhouse_id)
    #si es la ultima pide confirmacion para eliminar tambien el invernadero
    if len(areas) == 1:
        await update.callback_query.message.reply_text(
            "Esta es la última área del invernadero. ¿Estás seguro de que deseas eliminarla? Se eliminará el invernadero también.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("CONFIRMARAR AMBOS", callback_data='confirm_delete_both')],
                [InlineKeyboardButton("CANCELAR", callback_data='cancel_delete_both')]
            ])
        )
        return CONFIRM_X_BOTH
    else:
        await update.callback_query.message.reply_text(
            f"¿Estás seguro de que deseas eliminar el área con ID: {area_X}?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("CONFIRMAR", callback_data='confirm_delete_area')],
                [InlineKeyboardButton("CANCELAR", callback_data='cancel_delete_area')]
            ])
        )
        return CONFIRM_X_A

async def confirm_delete_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    greenhouse_id = user_data[user_id]['gh_to_manage']
    area_X = user_data[user_id]['area_to_delete']
    
    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    decision = query.data
    await query.edit_message_reply_markup(reply_markup=None)
    # Si elijo CONFIRMAR
    if decision == 'confirm_delete_area':
        if await delete_area(catalog_url, greenhouse_id, area_X):
            await update.callback_query.message.reply_text(f"Área con ID: {area_X} eliminada con éxito. Por ahora ADIOS")
            # Eliminar el área de la lista del invernadero
            #deberia volver al menu, por ahora finalizamos
            #return MAIN_MENU  # OR MANAGE_GH
            return ConversationHandler.END
        else:
            await update.callback_query.message.reply_text("Error al eliminar el área. Intenta nuevamente.")
            return CONFIRM_X_A
    elif decision == 'cancel_delete_area':
        await update.callback_query.message.reply_text("Eliminación cancelada.")
        del user_data[user_id]['area_to_delete']
        # Volver al menú principal
        await update.callback_query.message.reply_text(
            "Volvete al menú principal, daleee, linea 557.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL MENÚ PRINCIPAL", callback_data='back_to_main_menu')]])
        )
        return MAIN_MENU ##OR MANAGE_GH EN FUTURO
    else:
        await update.callback_query.message.reply_text("Error catastrofal. Por favor, intenta nuevamente. ADIOS 561")
        return ConversationHandler.END

async def confirm_delete_both(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    greenhouse_id = user_data[user_id]['gh_to_manage']
    area_X = user_data[user_id]['area_to_delete']
    
    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    decision = query.data
    await query.edit_message_reply_markup(reply_markup=None)

    # Si elijo CONFIRMAR
    if decision == 'confirm_delete_both':
        if await delete_entire_greenhouse(catalog_url, greenhouse_id):
            await update.callback_query.message.reply_text(f"Invernadero con ID: {greenhouse_id} y área con ID: {area_X} eliminados con éxito.")
            if any(gh['greenhouseID'] == greenhouse_id for gh in user_data[user_id]['their_greenhouses']):
                remove_greenhouse(user_id, greenhouse_id)
            else:
                print(f"Advertencia: el invernadero {greenhouse_id} no estaba en la lista del usuario {user_id}")
            del user_data[user_id]['area_to_delete']  # Eliminar la clave de user_data
            # Volver al menú principal
            await update.callback_query.message.reply_text(
                "Volviendo al menú principal. ADIOS",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL MENÚ PRINCIPAL", callback_data='back_to_main_menu')]])
            )
            return MAIN_MENU
        else:
            await update.callback_query.message.reply_text("Error al eliminar el invernadero. Intenta nuevamente.")
            return CONFIRM_X_BOTH
    elif decision == 'cancel_delete_both':
        await update.callback_query.message.reply_text("Eliminación cancelada.")
        del user_data[user_id]['area_to_delete']
        # Volver al menú principal
        await update.callback_query.message.reply_text(
            "Volviendo al menú principal. linea 586",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL MENÚ PRINCIPAL", callback_data='back_to_main_menu')]])
        )
        return MAIN_MENU ##OR MANAGE_GH EN FUTURO
    else:
        await update.callback_query.message.reply_text("Error catastrofal. Por favor, intenta nuevamente. ADIOS 650")
        return ConversationHandler.END


# async def handle_actions_invernadero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     # Aquí puedes manejar la lógica para las acciones del invernadero
#     pass

############################## Callback Query Handlers ##############################
async def handle_bye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data[user_id] = {}
    bye_msg = "Adiós! Hasta la próxima. ¡Gracias por elegirnos!"
    if update.message:
        await update.message.reply_text(bye_msg)
    elif update.callback_query:
        await update.callback_query.answer()
        #await query.edit_message_reply_markup(reply_markup=None)
        await update.callback_query.edit_message_text(bye_msg)
    print(f">> Usuario {user_id} finalizó la conversación.")
    return ConversationHandler.END

async def handle_back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id in user_data:
        user_data[user_id] = {}

    query = update.callback_query
    if query:
        await query.answer()
        # Eliminar los botones anteriores de ese mensaje
        await query.edit_message_reply_markup(reply_markup=None)
        # Enviar un nuevo mensaje con texto y botones nuevos
        await query.message.reply_text(
            "Regresando al menú principal. ¿Qué deseas hacer?",
            reply_markup=main_menu_keyboard
        )
    else:
        # Si no es callback, solo enviamos el mensaje nuevo con botones
        await update.message.reply_text(
            "Regresando al menú principal. ¿Qué deseas hacer?",
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
    #se comunica con el catalog y revisa la "currentTemperature".
    area = await get_area(catalog_url, greenhouse_id, area_processing)
    current_temperature = area['currentTemperature']
    current_humidity = area['currentHumidity']
    current_luminosity = area['currentLuminosity']
    
    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    to_verify = query.data  

    #Ofrece boton de back to main menu (back_to_MM) o de bye
    if to_verify == 'check_temperature':
        await update.callback_query.message.reply_text( #english
            f"Current temperature in area {area_processing} of greenhouse {greenhouse_id} is: {current_temperature}°C",
            reply_markup=end_markup
        )
    elif to_verify == 'check_luminosity':
        await update.callback_query.message.reply_text( #english
            f"Current luminosity in area {area_processing} of greenhouse {greenhouse_id} is: {current_luminosity}%",
            reply_markup=end_markup
        )
    elif to_verify == 'check_humidity':
        await update.callback_query.message.reply_text( #english
            f"Current humidity in area {area_processing} of greenhouse {greenhouse_id} is: {current_humidity}%",
            reply_markup=end_markup
        )
    return FINAL_STAGE

async def handle_actuators_a(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    greenhouse_id = user_data[user_id]['gh_to_manage']
    area_processing = user_data[user_id]['area_to_do']

    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    actuator_selection = query.data
    user_data[user_id]['actuator_selection'] = actuator_selection
    await query.edit_message_reply_markup(reply_markup=None)

    #it uses MQTT to send the command to the actuators
    #It should publish to the topic                 "pumpActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/pump",
                #"lightActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/light",
                #"ventilationActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/ventilation",
    
    #Ofrece boton de encender o apagar
    update.callback_query.message.reply_text(
        f"Do you want to turn on or off the actuators in area {area_processing} of greenhouse {greenhouse_id}?",
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
    #user_data[user_id]['state_wanted'] = to_set_on_off

    #Check if the actuator is already on or off
    state_a = await check_actuator_state(catalog_url, greenhouse_id, area_processing, actuator_selection)
    user_data[user_id]['actuator_state'] = state_a

    if actuator_selection == 'manage_pump':
        oki = await set_actuator(catalog_url, greenhouse_id, area_processing, "pumpActuation",to_set_on_off, publisherMQTT)
    elif actuator_selection == 'manage_light':
        oki = await set_actuator(catalog_url, greenhouse_id, area_processing, "lightActuation", to_set_on_off, publisherMQTT)
    elif actuator_selection == 'manage_fan':
        oki = await set_actuator(catalog_url, greenhouse_id, area_processing, "ventilationActuation", to_set_on_off, publisherMQTT)
    else:
        oki = await update.callback_query.message.reply_text("Invalid actuator. Please try again.",
                                                       reply_markup=(back_to_MM)
        )
        return FINAL_STAGE
    
    #check if to_set_on_off is 1 or 0 and convert it to on or off for showing to the user
    if to_set_on_off == 1:
        to_set_on_off_show = "ON"
    elif to_set_on_off == 0:
        to_set_on_off_show = "OFF"

    # Check the response from the MQTT publish
    if oki["status_code"] == 200:
        await update.callback_query.message.reply_text(
            f"Actuator {actuator_selection} in area {area_processing} of greenhouse {greenhouse_id} is now: {to_set_on_off_show}",
            reply_markup=end_markup
        )
    else:
        await update.callback_query.message.reply_text(f"Error sending MQTT command: {oki.get('error', 'unknown')}. Contact Support.",
                                                       reply_markup=end_markup
)
    return FINAL_STAGE

async def check_actuator_state(catalog_url, greenhouse_id, area_processing, actuator_type):
    try: #greenhouse1/areas/1  #greenhouse1/areas/1 
        response = get_area(catalog_url, greenhouse_id, area_processing)
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


async def set_actuator(update, catalog_url, greenhouse_id, area_processing, actuator_type, to_set_on_off, publisherMQTT):
    user_id = update.effective_user.id

    state_previous = user_data[user_id]['actuator_state']
    action_wanted = to_set_on_off

    if state_previous == action_wanted:
            await update.callback_query.message.reply_text(
                f"The actuator is already {state_previous}. No changes made. Return to Main Menu.",
                reply_markup=back_to_MM
            )
            return MAIN_MENU
    else:
            #Mqtt publish to 
                    #"pumpActuation": "greenhouse1/area2/actuation/pump",
                    #"lightActuation": "greenhouse1/area2/actuation/light",
                    #"ventilationActuation": "greenhouse1/area2/actuation/ventilation",
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
                    "Invalid actuator type. Please try again.",
                    reply_markup=(back_to_MM)
                )
                return None

            # Simulate sending the actuation command (replace with actual MQTT or API call)
            payload = {"state": to_set_on_off}
            response = publisherMQTT.publish(topic, payload)

            # Log the response for debugging
            print(f"Actuator command sent to {topic} with payload {payload}. Response: {response.status_code}")

            return response
        except Exception as e:
            print(f"Error while setting actuator state: {e}")
            await update.callback_query.message.reply_text(
                "An error occurred while setting the actuator state. Please try again.",
                reply_markup=(back_to_MM)
            )
            return None

    #state_a is 0 or 1 for "pump or ventialation" and on or off for light.


    # I should know what parameters I can give to the thingies.
    
############################# CLASSES #############################
class BotMain:
    def __init__(self, config):
        self.token = config['telegram_token']
        self.catalog_url = config['catalog_url']

        application = Application.builder().token(self.token).build()
        application.bot_data['catalog_url'] = self.catalog_url

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
                CREATE_A: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_create_first_a),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                    #CallbackQueryHandler(handle_back_to_create_gh, pattern='back_to_create_gh'),
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
                    CallbackQueryHandler(confirm_delete_area, pattern='confirm_delete_area'),
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
                ],
                WAIT_ACTUATOR_STATE: [
                    CallbackQueryHandler(partial(handle_actuator_state, publisherMQTT=MQTTBuddy), pattern='on'),
                    CallbackQueryHandler(partial(handle_actuator_state, publisherMQTT=MQTTBuddy), pattern='off'),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CONFIRM_X_BOTH: [
                    CallbackQueryHandler(confirm_delete_both, pattern='confirm_delete_both'),
                ],
                FINAL_STAGE: [
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                    CallbackQueryHandler(handle_bye, pattern='bye'),
                ],
            },
            fallbacks=[CommandHandler('start', start)]
        )

        application.add_handler(conv_handler)
        application.run_polling()

if __name__ == "__main__":
    config = load_config()
    #instance of MyMQTT
    MQTTBuddy = MyMQTTforBOT.MyMQTT(2903, config.get("mqtt_broker"), config.get("mqtt_port"))
    bot = BotMain(config)

