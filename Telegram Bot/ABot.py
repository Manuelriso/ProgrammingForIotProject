import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from datetime import datetime

# Estados del árbol de conversación
# MAIN_MENU, CREATE_GH, CREATE_A, INPUT_GH_ID, MANAGE_GH, MANAGE_AREA, CONFIRM_X_GH, ADD_A, DELETE_A, CONFIRM_X_A,  CONFIRM_X_BOTH = range(11)
MAIN_MENU, WAIT_NEW_GH_ID, WAIT_NEW_GH_PLANT, CREATE_A, INPUT_GH_ID, HANDLING_GH_ID, CONFIRM_X_GH, MANAGE_GH, SHOWING_AVAILABLE_AREAS, CHECKING_WHATTODO_AREA, CONFIRM_X_A, CONFIRM_X_BOTH, ADD_A, WAIT_AREA_INSTRUCTION = range(14)

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

A_Mg_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Verificar Humedad", callback_data='check_humidity')],
            [InlineKeyboardButton("Verificar Temperatura", callback_data='check_temperature')],
            [InlineKeyboardButton("Verificar Luminosidad", callback_data='check_luminosity')],
            [InlineKeyboardButton("Administrar Bomba", callback_data='manage_pump')],
            [InlineKeyboardButton("Administrar Ventilador", callback_data='manage_fan')],
            [InlineKeyboardButton("Administrar Luz", callback_data='manage_light')],
            [InlineKeyboardButton("ATRÁS", callback_data='back_to_manage_gh')]
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
            "greenhouseID": greenhouse_id,
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
                    "temperatureDataTopic": "greenhouse1/area1/temperature",
                    "humidityDataTopic": "greenhouse1/area1/humidity",
                    "luminosityDataTopic": "greenhouse1/area1/luminosity",
                    "motionTopic": "greenhouse1/area1/motion",
                    "motionDetected": 0,
                    "pumpActuation": "greenhouse1/area1/actuation/pump",
                    "lightActuation": "greenhouse1/area1/actuation/light",
                    "ventilationActuation": "greenhouse1/area1/actuation/ventilation",
                    "pump": 0,
                    "light": "off",
                    "ventilation": 0
                }
            ]
        }
        print(f"POST de nuevo greenhouse a: {catalog_url}greenhouse") 
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
            "humidityThreshold": 80, ########## THIS SHOULD BE A VARIABLE
            "temperatureThreshold": 21, ######### THIS SHOULD BE A VARIABLE
            "luminosityThreshold": 60, ############ THIS SHOULD BE A VARIABLE
            "plants": plant_type,
            "temperatureDataTopic": "greenhouse1/area1/temperature",
            "humidityDataTopic": "greenhouse1/area1/humidity",
            "luminosityDataTopic": "greenhouse1/area1/luminosity",
            "motionTopic": "greenhouse1/area1/motion",
            "motionDetected": 0,
            "pumpActuation": "greenhouse1/area1/actuation/pump",
            "lightActuation": "greenhouse1/area1/actuation/light",
            "ventilationActuation": "greenhouse1/area1/actuation/ventilation",
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
                    "creation_date": gh.get("creation_date", "Fecha desconocida")
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
        response = requests.delete(f"{catalog_url}greenhouses/{greenhouse_id}") #manca implementare in catalog.py
        if response.status_code == 204: ##TO check
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False
    
### Delete an area inside a greenhouse  (maybe unify with delete entire and work with callback to know what)
async def delete_area(catalog_url, greenhouse_id, area_id) -> bool:
    try:
        response = requests.delete(f"{catalog_url}greenhouses/{greenhouse_id}/areas/{area_id}") ####falta implementar en catalog.py
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
        print(f"Respuesta del servidor: {response.text}")  # Debug adicional
        if response.status_code == 200:
            data = response.json()  # Obtén el cuerpo de la respuesta
            areas = data.get("areas", [])  # Asegúrate de obtener el campo 'areas'
            print(f"Áreas obtenidas: {areas}")  # Ver las áreas que obtenemos del servidor
            if not areas:
                # Si no hay áreas, puedes lanzar un error o notificar de alguna forma
                print(f"Advertencia: El invernadero {greenhouse_id} no tiene áreas asociadas.")
                return []
            area_list = [(area['ID'], area['plants']) for area in areas]
            return area_list
        else:
            print(f"Error en la solicitud: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return []
    
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



############################### CONVERSATION STATES ###############################
# Inicio del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data[user_id] = {}
    await update.message.reply_text('Ahí llega el menú', reply_markup=ReplyKeyboardRemove())
    #Teclado de respuesta en area de texto
    await update.message.reply_text(f"Bienvenido! Tu ID es {user_id}. ¿Qué deseas hacer?", reply_markup=main_menu_keyboard)
    user_data[user_id]['their_greenhouses'] = await check_gh_ownership(user_id, context.bot_data['catalog_url'])
    return MAIN_MENU

####### CREATION PART ##########
###Manejo de ID de adición/creación de invernadero
async def handle_wait_new_gh_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> Entró a handle_wait_new_gh_id")
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    # Definir el botón "ATRÁS"
    back_button = InlineKeyboardButton("ATRÁS", callback_data='back_to_main_menu')
    # Usar InlineKeyboardMarkup con el botón adecuado
    markup = InlineKeyboardMarkup([[back_button]])

    # Luego, editar el mensaje con el teclado correcto
  # Always respond to the callback, even if empty
    await update.callback_query.message.reply_text(
        "Ingresa un ID numérico (máx 5 dígitos) o presiona ATRÁS. Estas en handlewaitnewGHID",
        reply_markup=markup
    )
    # Esperar la respuesta del usuario
    # Aquí puedes usar un MessageHandler para capturar el texto del usuario:
    return WAIT_NEW_GH_ID

async def handle_check_gh_id_and_wait_new_gh_plant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(">> Entró a handle_check_gh_id_and_wait_new_gh_plant")
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']

    gh_id = update.message.text.strip()
    
    if not (gh_id.isdigit() and len(gh_id) < 5):
        await update.message.reply_text("ID inválido. Debe ser numérico y tener máx 5 digitos. Intenta nuevamente.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_main_menu')]]) 
        )
        return WAIT_NEW_GH_ID
    # Verifica si el ID ya existe en la base de datos
    if await check_gh_id_exists(catalog_url, gh_id):
        await update.message.reply_text("Este ID ya está en uso. Elige otro.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_main_menu')]])                      
        )
        # El bot seguirá esperando automáticamente en este estado (CREATE_GH) debido a la estructura del ConversationHandler.
        # No necesitas agregar código adicional aquí para manejar el ingreso de texto del usuario.
        # El estado CREATE_GH ya está configurado para manejar mensajes de texto y volver a llamar a `handle_create_gh`.
        return WAIT_NEW_GH_ID

    # Si el ID es válido y no existe, lo guardamos en user_data
    user_data[user_id]['new_gh_id'] = gh_id
    await update.message.reply_text(f"¡ID aceptado! Tu invernadero tendrà el ID: {gh_id}. Diseñemos su primer área!",
    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_main_menu')]])
    )
    await update.message.reply_text(
        "Por favor, ingresa el tipo de planta para el área (máx 30 caracteres):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_create_gh')]])
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
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_create_gh')]])
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
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_main_menu')]])
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
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_main_menu')]])
        )
        return HANDLING_GH_ID

    # Verifica que el ID le pertenezca al usuario
    if not any(gh["greenhouseID"] == id_selected for gh in user_data[user_id]['their_greenhouses']):
        await update.message.reply_text(
        "Este GH no existe o no te pertenece. Elige de la lista.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_main_menu')]])
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
            [InlineKeyboardButton("ATRAS", callback_data='back_to_main_menu')]
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

    #Si elijo CONFIRMAR
    if decision == 'confirm_delete_gh':
        if await delete_entire_greenhouse(catalog_url, greenhouse_to_delete):
            await update.callback_query.message.reply_text(f"Invernadero con ID: {greenhouse_to_delete} eliminado con éxito.")
            user_data[user_id]['their_greenhouses'].remove(greenhouse_to_delete)  # Eliminar el invernadero de la lista del usuario
            del user_data[user_id]['gh_to_delete'] # Eliminar la clave de user_data
            # Volver al menú principal
            await update.callback_query.message.reply_text(
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL MENú principal por fabooor 365", callback_data='back_to_main_menu')]])
            )
            return MAIN_MENU
        else:
            await update.callback_query.message.reply_text("Error al eliminar el invernadero. Intenta nuevamente.")
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
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁSSSSSSSSSSSSSS", callback_data='back_to_main_menu')]])
            )
            return MAIN_MENU ##MANAGE_GH
    else:
            user_data[user_id]['new_area_id'] = available_id
            await update.callback_query.message.reply_text(f"El ID del área a agregar es: {available_id}. Por favor, ingresa el tipo de planta (máx 30 caracteres):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_manage_gh')]])
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
    print(f">> Acción seleccionada: {action}")

    user_data[user_id]['area_managing_desired_action'] = action

    print( ">> Se guardo en el user para area managing desired action: ", user_data[user_id]['area_managing_desired_action'])

    await update.callback_query.message.reply_text(
        f"Estas son las áreas del invernadero con ID: {greenhouse_id}.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_manage_gh')]])
        )
        
    areas = await list_areas(catalog_url, greenhouse_id)
    area_list = "\n".join([f"Área ID: {area[0]}, Plantas: {area[1]}" for area in areas])
    await update.callback_query.message.reply_text(area_list)
        # Markup de gestion y eliminacion,  e intervencion, crear botones dinámicamente para cada área en la lista
    

    
    markup = [
        [InlineKeyboardButton(f"{area[0]} {area[1]}", callback_data=f"area_{area[0]}")]
        for area in areas
        ]
    markup.append(back_to_MM)

    if action == 'gestion_areas':
        print(">> Entró a gestionar áreas linea 450")
        await update.callback_query.message.reply_text(
            "Selecciona un área para gestionar:",
            reply_markup=InlineKeyboardMarkup(markup)
        )
    elif action == 'eliminacion_area':
        print(">> Entró a eliminar áreas linea 455")
        await update.callback_query.message.reply_text(
            "Selecciona un área para eliminar:",
            reply_markup=InlineKeyboardMarkup(markup)
        )
    elif action == 'acciones_invernadero':
        print(">> Entró a acciones invernadero linea 460")
        await update.callback_query.message.reply_text(
            "Selecciona un área para INTERVENIR:",
            reply_markup=InlineKeyboardMarkup(markup)
        )
    return SHOWING_AVAILABLE_AREAS

async def checking_what_to_do_showed_areas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']
    
    print(">> Entró a checking_what_to_do_showed_areas")
    query = update.callback_query
    await query.answer()  # Siempre respondé el callback aunque sea vacío
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
        await update.callback_query.message.reply_text(f"¿Estás seguro de que deseas eliminar el área con ID: {id_to_do}?",
                reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("CONFIRMAR", callback_data='confirm_delete_area')],
                [InlineKeyboardButton("CANCELAR", callback_data='cancel_delete_area')]
            ]))
        return CONFIRM_X_A

    elif next_step == 'acciones_invernadero':
        user_data[user_id]['area_to_intervene'] = id_to_do
        #funcion no implementada aun, adios
        await update.callback_query.message.reply_text("Funcionalidad no implementada todavía. ADIOS")
        return ConversationHandler.END
    else:
        await update.callback_query.message.reply_text("Opción no válida. Por favor, intenta nuevamente. ADIOSSSSSS 497")
        return ConversationHandler.END 
    

async def handle_wait_new_a_plant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    catalog_url = context.bot_data['catalog_url']
    greenhouse_id = user_data[user_id]['gh_to_manage']
    new_id = user_data[user_id]['new_area_id']

    plant_type = update.message.text.strip()
    # Verifica que el tipo de planta no exceda los 30 caracteres
    if (len(plant_type) > 30 or not plant_type.isalnum()):
        await update.message.reply_text("Error: no superar los 30 caracteres, solo se permiten letras y números, intente nuevamente",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ATRÁS", callback_data='back_to_manage_gh')]])
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

    # Si elijo CONFIRMAR
    if decision == 'confirm_delete_both':
        if await delete_entire_greenhouse(catalog_url, greenhouse_id):
            await update.callback_query.message.reply_text(f"Invernadero con ID: {greenhouse_id} y área con ID: {area_X} eliminados con éxito.")
            # Eliminar el invernadero de la lista del usuario
            user_data[user_id]['their_greenhouses'].remove(greenhouse_id)
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
        await update.callback_query.edit_message_text(bye_msg)
    print(f">> Usuario {user_id} finalizó la conversación.")
    return ConversationHandler.END


async def handle_back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    # Clear user-specific data if necessary
    if user_id in user_data:
        user_data[user_id] = {}
    # Handle the callback query
    query = update.callback_query
    if query:
        await query.answer()  # Respond to the callback query
        # Edit the message to show the main menu
        await query.edit_message_text("Regresando al menú principal. ¿Qué deseas hacer?", reply_markup=main_menu_keyboard)
    else:
        # If no callback query, send a new message with the main menu
        await update.message.reply_text("Regresando al menú principal. ¿Qué deseas hacer?", reply_markup=main_menu_keyboard)
    return MAIN_MENU

# async def handle_back_to_create_gh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     user_data[update.effective_user.id] = {} ### REVISAR
#     await update.message.reply_text("Regresando a la creación del invernadero...")
#     return CREATE_GH

async def handle_acciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Aquí puedes manejar la lógica para las acciones del invernadero
    await update.callback_query.message.reply_text("Funcionalidad no implementada todavía. FINALIZANDO")
    return ConversationHandler.END

async def handle_verify_humidity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Aquí puedes manejar la lógica para verificar la humedad
    await update.callback_query.message.reply_text("Funcionalidad no implementada todavía. FINALIZANDO")
    return ConversationHandler.END

async def handle_verify_temperature(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Aquí puedes manejar la lógica para verificar la temperatura
    await update.callback_query.message.reply_text("Funcionalidad no implementada todavía. FINALIZANDO")
    return ConversationHandler.END

async def handle_verify_luminosity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Aquí puedes manejar la lógica para verificar la luminosidad
    await update.callback_query.message.reply_text("Funcionalidad verify no implementada todavía. FINALIZANDO")
    return ConversationHandler.END

async def handle_manage_pump(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Aquí puedes manejar la lógica para administrar el ventilador
    await update.callback_query.message.reply_text("Funcionalidad manage pump no implementada todavía. FINALIZANDO")
    return ConversationHandler.END

async def handle_manage_fan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Aquí puedes manejar la lógica para administrar el ventilador
    await update.callback_query.message.reply_text("Funcionalidad manage fan no implementada todavía. FINALIZANDO")
    return ConversationHandler.END

async def handle_manage_light(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Aquí puedes manejar la lógica para administrar la luz
    await update.message.reply_text("Funcionalidad manage light no implementada todavía. FINALIZANDO")
    return ConversationHandler.END



############################# CLASSES #############################
class BotMain:
    def __init__(self, config):
        self.token = config['telegram_token']
        self.catalog_url = config['catalog_url']

        application = Application.builder().token(self.token).build()
        application.bot_data['catalog_url'] = self.catalog_url

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
                CHECKING_WHATTODO_AREA: [
                    CallbackQueryHandler(handle_verify_humidity, pattern='check_humidity'),
                    CallbackQueryHandler(handle_verify_temperature, pattern='check_temperature'),
                    CallbackQueryHandler(handle_verify_luminosity, pattern='check_luminosity'),
                    CallbackQueryHandler(handle_manage_pump, pattern='manage_pump'),
                    CallbackQueryHandler(handle_manage_fan, pattern='manage_fan'),
                    CallbackQueryHandler(handle_manage_light, pattern='manage_light'),
                    CallbackQueryHandler(handle_back_to_main_menu, pattern='back_to_main_menu'),
                ],
                CONFIRM_X_BOTH: [
                    CallbackQueryHandler(confirm_delete_both, pattern='confirm_delete_both'),
                ],
            },
            fallbacks=[CommandHandler('start', start)]
        )

        application.add_handler(conv_handler)
        application.run_polling()

if __name__ == "__main__":
    config = load_config()
    bot = BotMain(config)

