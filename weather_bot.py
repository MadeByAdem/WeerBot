import os
import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
import telebot
from telebot import types
from cryptography.fernet import Fernet, InvalidToken
import weather_functions

load_dotenv()

# ENV VARIABLES
SECRET_TOKEN_WEATHERBOT = os.getenv("SECRET_TOKEN_WEATHERBOT")

CHAT_ID_PERSON_1 = int(os.getenv("CHAT_ID_PERSON_1"))
CHAT_ID_PERSON_2 = int(os.getenv("CHAT_ID_PERSON_2"))
AUTORIZED_USERS = [CHAT_ID_PERSON_1, CHAT_ID_PERSON_2]

bot = telebot.TeleBot(SECRET_TOKEN_WEATHERBOT, parse_mode='html')

SSHKEY = os.getenv("SSHKEY")

RECEIVING_SERVER = os.getenv("RECEIVING_SERVER").split(":")[0]
RECEIVING_PORT = os.getenv("RECEIVING_SERVER").split(":")[1]
RECEIVING_FILE_PATH = os.getenv("RECEIVING_FILE_PATH")

LOG_DIRECTORY = os.getenv("LOG_DIRECTORY")
LOG_FILE_NAME = os.getenv("LOG_FILE_NAME")
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, LOG_FILE_NAME)

KNMI_API_KEY = os.getenv("KNMI_API_KEY")
KNMI_LOCATION_CODE = os.getenv("KNMI_LOCATION_CODE")

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

AUTHORIZED_USERS = [CHAT_ID_PERSON_1, CHAT_ID_PERSON_2]


commands_telegram = """
<b>Menu</b> - Toon het menu
/menu

<b>Start</b> - Start de bot
/start
"""

@bot.message_handler(commands=['start'], func=lambda message: message.chat.id in AUTHORIZED_USERS)
def send_start(message):
    logging.info(f"User {message.from_user.first_name} ({message.from_user.id}) started the bot")
    global commands_telegram
    welcome_message = f"""Hey {message.from_user.first_name}, 
    
Ik ben een Weer Bot.

Twee keer per uur log in weer gegevens en een paar keer per dag wat gedetaillerder. Je kunt deze gegevens ook handmatig opvragen.

Je vind deze functies in het menu.
{commands_telegram}"""

    bot.send_message(message.chat.id, welcome_message)
    send_handle_menu(message)


@bot.message_handler(commands=['menu'], func=lambda message: message.chat.id in AUTHORIZED_USERS)
def send_handle_menu(message):
    markup_menu = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    
    # Add buttons
    button1 = telebot.types.KeyboardButton('😎 Het weer samengevat')
    button2 = telebot.types.KeyboardButton('📒 Gedetailleerde gegevens')

    
    markup_menu.add(button1, button2)
    
    option_selection_text = 'Wat wil je doen?'
    
    bot.send_message(message.chat.id, option_selection_text, reply_markup=markup_menu)

@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == '😎 Het weer samengevat')
def send_handle_weather_summary(message):
    logging.debug("Weather summary function requested.")
    weather_data, weather_data_raw = weather_functions.get_weather_data()
    weather_functions.store_weather_data(weather_data)
    weather_message = weather_functions.create_weather_message_summary(weather_data)
    bot.send_message(message.chat.id, weather_message)
    
    weather_functions.send_weather_data(SSHKEY, RECEIVING_PORT, RECEIVING_SERVER, RECEIVING_FILE_PATH)
    
    logging.debug("Weather summary request function ended.")
    send_handle_menu(message)
    

@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == '📒 Gedetailleerde gegevens')
def send_handle_weather_details(message):
    logging.debug("Weather details function requested.")
    weather_data, weather_data_raw = weather_functions.get_weather_data()
    weather_functions.store_weather_data(weather_data)
    weather_message = weather_functions.create_weather_message_details(weather_data)
    bot.send_message(message.chat.id, weather_message)
    
    weather_functions.send_weather_data(SSHKEY, RECEIVING_PORT, RECEIVING_SERVER, RECEIVING_FILE_PATH)
    
    logging.debug("Weather details request function ended.")
    send_handle_menu(message)

# Handle all other messages to all users
@bot.message_handler(func=lambda message: True)
def handle_all_other_messages(message):
    logging.debug(f"Handle_all_other_messages function started.")
    logging.info(f"User is asked for input: {message.text}")
        
    bot.reply_to(message, "Sorry, I didn't understand that. Type /menu to see what I can do.")
    if message.chat.id in AUTHORIZED_USERS:
        send_handle_menu(message)
    else:
        bot.reply_to(message.chat.id, "Sorry, it looks like you're not authorized.")
    
    logging.debug(f"Handle_all_other_messages function ended.")
    
print("Bot running...")
logging.info("Bot running...")
bot.polling()