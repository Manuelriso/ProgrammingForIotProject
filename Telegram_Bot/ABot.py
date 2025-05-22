import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from datetime import datetime

# Estados del árbol de conversación
# MAIN_MENU, CREATE_GH, CREATE_A, INPUT_GH_ID, MANAGE_GH, MANAGE_AREA, CONFIRM_X_GH, ADD_A, DELETE_A, CONFIRM_X_A,  CONFIRM_X_BOTH = range(11)
MAIN_MENU, WAIT_NEW_GH_ID, WAIT_NEW_GH_PLANT, CREATE_A, INPUT_GH_ID, HANDLING_GH_ID, CONFIRM_X_GH, MANAGE_GH, SHOWING_AVAILABLE_AREAS, CONFIRM_X_A, CONFIRM_X_BOTH, ADD_A, WAIT_AREA_INSTRUCTION, FINAL_STAGE = range(14)

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
async def check_gh_id_exists(catalog_url, greenhouse_id) -> bool:
    try:
        response = requests.get(f"{catalog_url}greenhouses")
        if response.status_code == 200:
            greenhouses = response.json().get("greenhouses", [])
            return any(str(gh['greenhouseID']) == greenhouse_id for gh in greenhouses)
        return False  # Cambiado a False, ya que no se encontró el ID y no hubo error
    except requests.exceptions.RequestException:
        return True  # Mantener True para manejar errores de conexión

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
    
### List the areas and their plants asociated, inside a greenhouse
# async def list_areas(catalog_url, greenhouse_id) -> list:
#     try:
#         response = requests.get(f"{catalog_url}greenhouse{greenhouse_id}/areas")
#         print(f"Respuesta del servidor: {response.text}")  # Agregar debug aquí
#         if response.status_code == 200:
#             areas = response.json().get("areas", [])
#             print(f"Áreas encontradas: {areas}")  # Mostrar áreas encontradas
#             area_list = [(area['ID'], area['plants']) for area in areas]
#             return area_list
#         return []
#     except requests.exceptions.RequestException as e:
#         print(f"Error en la solicitud: {e}")
#         return []


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



# if response.status_code == 200:
#     data = response.json()  # Obtén el cuerpo de la respuesta
#     areas = data.get("areas", [])  # Esto asegura que 'areas' exista y sea una lista vacía si no está presente
#     if areas:
#         area_list = [(area['ID'], area['plants']) for area in areas]
#         return area_list
#     else:
#         print(f"Advertencia: El invernadero {greenhouse_id} no tiene áreas asociadas.")
#         return []
# else:
#     print(f"Error en la solicitud: {response.status_code}")
#     return []

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
    await update.message.reply_text('GREENHOUSE ALLA PUGLIA', reply_markup=ReplyKeyboardRemove())
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
        await update.message.reply_text("Este ID ya está en uso. Elige otro.",
        reply_markup=back_to_MM                      
        )
        # El bot seguirá esperando automáticamente en este estado (CREATE_GH) debido a la estructura del ConversationHandler.
        # No necesitas agregar código adicional aquí para manejar el ingreso de texto del usuario.
        # El estado CREATE_GH ya está configurado para manejar mensajes de texto y volver a llamar a `handle_create_gh`.
        return WAIT_NEW_GH_ID

    # Si el ID es válido y no existe, lo guardamos en user_data
    user_data[user_id]['new_gh_id'] = gh_id
    await update.message.reply_text(f"¡ID aceptado! Tu invernadero tendrà el ID: {gh_id}. Diseñemos su primer área!",
    reply_markup=InlineKeyboardMarkup(back_to_MM)
    )
    await update.message.reply_text(
        "Por favor, ingresa el tipo de planta para el área (máx 30 caracteres):",
        reply_markup=InlineKeyboardMarkup(back_to_MM)
    )
    return CREATE_A

### Create the first area of the greenhouse
async def handle_create_first_a(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> Entró a handle_create_first_a")
    catalog_url = context.bot_data['catalog_url']
    user_id = update.effective_user.id
    gh_id = user_data[user_id]['new_gh_id']

    plant_type = update.message.text.strip()
    
    # Verifica que el tipo de planta no exceda los 30 caracteres
    if (len(plant_type) > 30 or not plant_type.isalnum()):
        await update.message.reply_text("Error: no superar los 30 caracteres, solo se permiten letras y números, intente nuevamente",
        reply_markup=InlineKeyboardMarkup(back_to_MM)
        )
        return CREATE_A
    
    # Llamar a la función para crear el invernadero y el área
    success = await create_greenhouse_and_area(catalog_url, user_id, gh_id, plant_type) # await not necesary apparently
    
    if success:
        await update.message.reply_text(f"¡Invernadero creado con éxito! ID: {gh_id}.\nSu primer área tiene plantas del tipo: {plant_type}.")
        del user_data[user_id]['new_gh_id']  # Eliminar la clave de user_data
        # Volver al menú principal
        await update.message.reply_text(
            "Invernadero creado con éxito. Volviendo al menú principal.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL MENÚ PRINCIPAL", callback_data='back_to_main_menu')]])
        )
        return MAIN_MENU
    else:
        await update.message.reply_text("Error al crear el invernadero. Intenta nuevamente. linea 260")
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

    #lista los invernaderos del usuario
    user_data[user_id]['their_greenhouses'] = await check_gh_ownership(user_id, context.bot_data['catalog_url'])
    # Si no tiene invernaderos, envía un mensaje y vuelve al menú principal
    if not user_data[user_id]['their_greenhouses']:
        await update.callback_query.message.reply_text(
            "No tienes invernaderos. Por favor, regresa y crea uno primero.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL MENU PRINCIPAL", callback_data='back_to_main_menu')]])
        )
        return MAIN_MENU
    # Lista los invernaderos del usuario y pide el ID
    #gh_list = "\n".join(f"-> {gh}" for gh in user_data[user_id]['their_greenhouses'])
    gh_list = "\n".join(
    f"-> {gh['greenhouseID']} (creado el {gh['creation_date']})"
    for gh in sorted(user_data[user_id]['their_greenhouses'], key=lambda x: int(x['greenhouseID']))
)
    await update.callback_query.message.reply_text(
        f"Estos son tus invernaderos:\n{gh_list}\n\nEscribe el ID del invernadero que deseas gestionar o eliminar:",
        reply_markup=InlineKeyboardMarkup(back_to_MM)
    )
    # Espera la respuesta del usuario
    return HANDLING_GH_ID

async def handle_gh_id_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> Entró a handle_gh_id_selection")
    user_id = update.effective_user.id

    id_selected = update.message.text.strip()
    # Verifica si el ID es válido, si es un número y tiene un máximo de 5 dígitos
    if not (id_selected.isdigit() and len(id_selected) < 5):
        del id_selected #is this necesary?
        await update.message.reply_text("ID inválido. Debe ser numérico y tener máx 5 digitos. Intenta nuevamente.",
        reply_markup=InlineKeyboardMarkup(back_to_MM)
        )
        return HANDLING_GH_ID

    # Verifica que el ID le pertenezca al usuario
    if not any(gh["greenhouseID"] == id_selected for gh in user_data[user_id]['their_greenhouses']):
        await update.message.reply_text(
            "Este GH no existe o no te pertenece. Elige de la lista.",
            reply_markup=InlineKeyboardMarkup(back_to_MM)
        )
        return HANDLING_GH_ID


    action = user_data[user_id]['action'] # 'delete_greenhouse' or 'manage_greenhouses'

    # Si el ID es válido y existe, lo guardamos en user_data
    if action == 'delete_greenhouse':
        user_data[user_id]['gh_to_delete'] = id_selected
        # g_gh_id = user_data[user_id]['gh_to_delete']
        await update.message.reply_text(f"¡ID aceptado! El invernadero a eliminar es: {id_selected}.")
        await update.message.reply_text(f"¿Estás seguro de que deseas eliminar el invernadero con ID: {id_selected}?",
                reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("CONFIRMAR", callback_data='confirm_delete_gh')],
                [InlineKeyboardButton("CANCELAR", callback_data='cancel_delete_gh')]
            ]))
        return CONFIRM_X_GH

    elif action == 'manage_greenhouses':
        user_data[user_id]['gh_to_manage'] = id_selected
        # g_gh_id = user_data[user_id]['gh_to_manage']
        await update.message.reply_text(f"¡ID aceptado! El invernadero a gestionar es: {id_selected}.")
        await update.message.reply_text(f"Has seleccionado el invernadero con ID: {id_selected}. ¿Qué deseas hacer?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Gestionar Areas", callback_data='gestion_areas')],
            [InlineKeyboardButton("Agregar Areas", callback_data='agregar_areas')],
            [InlineKeyboardButton("Eliminar Area", callback_data='eliminacion_area')],
            [InlineKeyboardButton("Acciones Invernadero", callback_data='acciones_invernadero')],
            [InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')]
        ])
        )
        return MANAGE_GH #NOT MANAGE_GH

####### Deleting an GH section #######
### Delete Greenhouse
async def handle_delete_gh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_to_delete = user_data[user_id]['gh_to_delete']

    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    decision = query.data    #YES OR NO
    await query.edit_message_reply_markup(reply_markup=None)

    #Si elijo CONFIRMAR
    if decision == 'confirm_delete_gh':
        print("entraste al dcision de confirm 452")
        if await delete_entire_greenhouse(catalog_url, greenhouse_to_delete):
            await update.callback_query.message.reply_text(f"Invernadero con ID: {greenhouse_to_delete} eliminado con éxito.")
            user_data[user_id]['their_greenhouses'] = [
                gh for gh in user_data[user_id]['their_greenhouses'] 
                if gh['greenhouseID'] != greenhouse_to_delete
            ]
            # Eliminar el invernadero de la lista del usuario
            del user_data[user_id]['gh_to_delete'] # Eliminar la clave de user_data
            # Volver al menú principal
            await update.callback_query.message.reply_text(
                "Volviendo al menú principal...",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL MENú principal por fabooor 458", callback_data='back_to_main_menu')]])
            )
            return MAIN_MENU
        else:
            await update.callback_query.message.reply_text("Error al eliminar el invernadero. Intenta nuevamente. linea 462")
            return CONFIRM_X_GH
    elif decision == 'cancel_delete_gh':
        await update.callback_query.message.reply_text("Eliminación cancelada.")
        del user_data[user_id]['gh_to_delete']
        #Volver al menú pincipal
        await update.callback_query.message.reply_text(
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL MENú principal ahorita 376", callback_data='back_to_main_menu')]])
        )
        return MAIN_MENU
    else:
        await update.callback_query.message.reply_text("Opción no válida. Por favor, intenta nuevamente. ADIOS")
        return ConversationHandler.END

######## Managing Greenhouse section ########
### Manage Add area
async def handle_add_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']
    #user_data[user_id]['area_to_add'] = None #Either this line or not use a BACK button

    # Enviar el mensaje con los botones generados
    print(">> Entró a agregar áreas liena 410")
    await update.callback_query.message.reply_text(
            "Agregemos un área para agregar bb:",
            reply_markup=InlineKeyboardMarkup(back_to_MM)
        )
    available_id = await next_area_id(catalog_url, greenhouse_id)

    if available_id == 0:
            await update.callback_query.message.reply_text("El invernadero ya tiene 4 áreas. No se pueden agregar más. .\n Por favor agrega un nuevo invernadero.")
            await update.callback_query.message.reply_text(
                "Por favor, regresa al menú principal o veremos.",
                reply_markup=InlineKeyboardMarkup(back_to_MM)
            )
            return MAIN_MENU ##MANAGE_GH
    else:
            user_data[user_id]['new_area_id'] = available_id
            await update.callback_query.message.reply_text(f"El ID del área a agregar es: {available_id}. Por favor, ingresa el tipo de planta (máx 30 caracteres):",
            reply_markup=InlineKeyboardMarkup(back_to_MM)
            )
            return ADD_A
         ########


### Manage Greenhouse
async def handle_manage_gh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']

    print(">> Entró a handle_manage_gh")
    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    action = query.data
    await query.edit_message_reply_markup(reply_markup=None)
    print(f">> Acción seleccionada: {action}")

    user_data[user_id]['area_managing_desired_action'] = action

    print( ">> Se guardo en el user para area managing desired action: ", user_data[user_id]['area_managing_desired_action'])

    await update.callback_query.message.reply_text(
        f"Estas son las áreas del invernadero con ID: {greenhouse_id}."
        )
    
       # Obtengo las áreas
    areas = await list_areas(catalog_url, greenhouse_id)
    #area_list = "\n".join([f"Área: {area[0]} - {area[1]}" for area in areas])

    # Construyo markup de áreas (botones)
    buttons_areas = [
        InlineKeyboardButton(f"{area[0]} - {area[1]}", callback_data=f"area_{area[0]}")
        for area in areas
    ]
    markup_areas = [buttons_areas[i:i + 2] for i in range(0, len(buttons_areas), 2)]
    markup_areas.append([InlineKeyboardButton("BACK TO MAIN MENU", callback_data='back_to_main_menu')])

        # Texto según la acción
    if action == 'gestion_areas':
        prompt = f"Gestiona las áreas del invernadero ID {greenhouse_id}:"
    elif action == 'eliminacion_area':
        prompt = f"Elige un área para eliminar del invernadero ID {greenhouse_id}:"
    elif action == 'acciones_invernadero':
        prompt = f"Selecciona un área para intervenir en invernadero ID {greenhouse_id}:"
    else:
        prompt = f"Áreas del invernadero ID {greenhouse_id}:"

    # Edito el mensaje original para mostrar texto + botones
    await query.edit_message_text(
        text=prompt,
        reply_markup=InlineKeyboardMarkup(markup_areas)
    )
    return SHOWING_AVAILABLE_AREAS

async def checking_what_to_do_showed_areas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']
    
    print(">> Entró a checking_what_to_do_showed_areas")
    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
    await query.edit_message_reply_markup(reply_markup=None)
    id_to_do = query.data.split("_")[1] # Splits decision in ["area", "area_id"] and takes the [1]=id
    user_data[user_id]['area_to_do'] = id_to_do

    next_step = user_data[user_id]['area_managing_desired_action']

    # Si elijo gestionar áreas
    if next_step == 'gestion_areas':
        await update.callback_query.message.reply_text(f"Has seleccionado el área con ID: {user_data[user_id]['area_to_manage']}. Elije que hacer a continuación:",
        reply_markup=A_Mg_markup
        )
        return WAIT_AREA_INSTRUCTION

    # Si elijo agregar áreas
    elif next_step == 'eliminacion_area':
        user_data[user_id]['area_to_delete'] = id_to_do
        await update.callback_query.message.reply_text(f"Are you sure you want to delete the area with ID: {id_to_do}?",
                reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("CONFIRM", callback_data='confirm_delete_area')],
                [InlineKeyboardButton("CANCEL", callback_data='cancel_delete_area')]
            ]))
        return CONFIRM_X_A

    elif next_step == 'acciones_invernadero':
        user_data[user_id]['area_to_intervene'] = id_to_do
        # Function not implemented yet, goodbye
        await update.callback_query.message.reply_text("Functionality not implemented yet. GOODBYE")
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
    # Verifica que el tipo de planta no exceda los 30 caracteres
    if (len(plant_type) > 30 or not plant_type.isalnum()):
        await update.message.reply_text("Error: do not exceed 30 characters, only letters and numbers are allowed, please try again",
        reply_markup=InlineKeyboardMarkup(back_to_MM)
        )
        del plant_type
        return ADD_A
    
    #user_data[user_id]['plant_type'] = plant_type
    if await create_area(catalog_url, greenhouse_id, new_id, plant_type):
        await update.message.reply_text(f"¡Area creada con éxito! ID: {user_data[user_id]['new_area_id']}."+".\n"+"Tiene plantas del tipo: {plant_type}.")
    else:
        await update.message.reply_text("Error al crear el area LINEA 524. Intenta nuevamente.")
        return ADD_A ### MANEJARLO MEJOR.
    del user_data[user_id]['new_area_id'] # Eliminar la clave de user_data
    # Volver al menú principal
    await update.message.reply_text(
        "Ahora toca volver al menu principal. linea 544",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL MENÚ PRINCIPAL", callback_data='back_to_main_menu')]])
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
    #it uses MQTT to send the command to the actuators
    #It should publish to the topic                 "pumpActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/pump",
                #"lightActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/light",
                #"ventilationActuation": f"greenhouse{int(greenhouse_id)}/area1/actuation/ventilation",
    
    if actuator_selection == 'manage_pump':
        await set_actuator(catalog_url, greenhouse_id, area_processing, "pumpActuation",to_set_on_off)
    elif actuator_selection == 'manage_light':
        await set_actuator(catalog_url, greenhouse_id, area_processing, "lightActuation", to_set_on_off)
    elif actuator_selection == 'manage_fan':
        await set_actuator(catalog_url, greenhouse_id, area_processing, "ventilationActuation", to_set_on_off)
    else:
        await update.callback_query.message.reply_text("Invalid actuator. Please try again.",
                                                       reply_markup=InlineKeyboardMarkup(back_to_MM)
        )
        return FINAL_STAGE
    
    if response.status_code == 200:
        await update.callback_query.message.reply_text(
            f"Actuators {to_set_on_off} in area {area_processing} of greenhouse {greenhouse_id} are now: {to_set_on_off}",
            reply_markup=end_markup
        )
    return FINAL_STAGE
    
async def set_actuator(catalog_url, greenhouse_id, area_processing, actuator_type, to_set_on_off):
    # I should know what parameters I can give to the thingies.
    return None

############################# CLASSES #############################
class BotMain:
    def __init__(self, config):
        self.token = config['telegram_token']
        self.catalog_url = config['catalog_url']

        application = Application.builder().token(self.token).build()
        application.bot_data['catalog_url'] = self.catalog_url

        self.notifier = TelegramAlertNotifier(application, self.catalog_url)
        self.mqtt_client = MyMQTT("BotAlertListener", self.mqtt_broker, self.mqtt_port, self.notifier)


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
    bot = BotMain(config)

