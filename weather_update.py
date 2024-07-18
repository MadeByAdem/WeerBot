import os
import logging
from logging.handlers import TimedRotatingFileHandler
import schedule
from dotenv import load_dotenv
import telebot
import time
from cryptography.fernet import Fernet, InvalidToken
import weather_functions

load_dotenv()


# ENV VARIABLES
SECRET_TOKEN_WEATHERBOT = os.getenv("SECRET_TOKEN_WEATHERBOT")

CHAT_ID_PERSON_1 = os.getenv("CHAT_ID_PERSON_1")
CHAT_ID_PERSON_2 = os.getenv("CHAT_ID_PERSON_2")
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

# Create users list directory
if not os.path.exists("/users_lists"):
    os.makedirs("/users_lists")

# Create users_details.txt and users_summary.txt if they don't exist
if not os.path.exists("/users_lists/users_details.txt"):
    with open("/users_lists/users_details.txt", "w") as users_details_file:
        users_details_file.write("")
if not os.path.exists("/users_lists/users_summary.txt"):
    with open("/users_lists/users_summary.txt", "w") as users_summary_file:
        users_summary_file.write("")


def weather_update(kind_of_update):
    logging.debug(f"Weather update {kind_of_update} function started.")
    weather_data, weather_data_raw = weather_functions.get_weather_data()
       
    if "Error" in weather_data and weather_data["Error"]:
        logging.error("Weather data could not be fetched the second time. Aborting storing and sending the information.")
        logging.error(weather_data)

        weather_functions.send_error_message(weather_data)
    else:
        logging.info("Weather data successfully fetched. Storing and sending the information.")
        weather_functions.store_weather_data(weather_data_raw)
        weather_functions.send_weather_data(SSHKEY, RECEIVING_PORT, RECEIVING_SERVER, RECEIVING_FILE_PATH)
        
        if kind_of_update == "summary":
            weather_functions.send_weather_message_summary(weather_data)
        elif kind_of_update == "details":
            weather_functions.send_weather_message_details(weather_data)
            
                           
    logging.debug(f"Weather update {kind_of_update} function ended.")
    logging.info("-----------------------------------------------------------------------------------------------")


weather_update("details")

# Generate a list of 30-minute intervals starting from 
thirty_minute_intervals = ["{:02d}:{:02d}".format(hour, minute) for hour in range(0, 24) for minute in range(28, 60, 30)]

for interval in thirty_minute_intervals:
    if interval == "05:58" or interval == "11:58" or interval == "14.58" or interval == "17:58" or interval == "21:58":
        schedule.every().day.at(interval).do(weather_update, "details")
    else:
        schedule.every().day.at(interval).do(weather_update, "summary")

while True:
    schedule.run_pending()
    time.sleep(60)