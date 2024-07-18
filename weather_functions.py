import json
import requests
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
import subprocess
import html
import telebot
import time
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime, timezone, timedelta

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

WEATHER_JSON_FILE_PATH = os.getenv("WEATHER_JSON_FILE_PATH")

UV_API_KEY = os.getenv("UV_API_KEY")
UV_API_BACKUP_KEY = os.getenv("UV_API_BACKUP_KEY")

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# LOGGING SETUP
# Ensure the log directory exists
os.makedirs(LOG_DIRECTORY, exist_ok=True)

# Use TimedRotatingFileHandler to create a new log file every day
handler = TimedRotatingFileHandler(
    LOG_FILE_PATH, when="midnight", interval=1, backupCount=7)
handler.suffix = "%Y-%m-%d.log"  # Add a suffix with the date format

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Set the logging level
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Add the handler to the logger
logger.addHandler(handler)


def get_UV_data():
    logging.debug("Get UV data function started.")
    lat = KNMI_LOCATION_CODE.split(",")[0]
    lon = KNMI_LOCATION_CODE.split(",")[1]
    uv_url = f"https://api.openuv.io/api/v1/uv?lat={lat}&lng={lon}&alt=0"

    headers = {
        "x-access-token": UV_API_KEY
    }

    try:
        # Attempt to fetch data using primary API key
        response = requests.get(uv_url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise HTTPError for bad responses

        data = response.json()
        return process_uv_data(data)


    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 403:
            logging.warning(
                f"Primary API key limit reached. Trying backup API key.")
            try:
                headers["x-access-token"] = UV_API_BACKUP_KEY
                response = requests.get(uv_url, headers=headers, timeout=30)
                response.raise_for_status()

                data = response.json()

                logging.debug("Get UV data function ended (using backup API key).")

                return process_uv_data(data)

            except requests.exceptions.HTTPError as http_err:
                logging.error(
                    f"Both API keys failed. Error fetching data from OpenUV API: {http_err}")
                data = load_data_from_json()
                return process_uv_data(data)
            except Exception as e:
                logging.error(
                    f"Error fetching data from OpenUV API with backup key: {e}")
                data = load_data_from_json()
                return process_uv_data(data)
        else:
            logging.error(f"HTTP error occurred: {http_err}")
            data = load_data_from_json()
            return process_uv_data(data)

    except requests.RequestException as e:
        logging.error(f"Error fetching data from OpenUV API: {e}")
        data = load_data_from_json()
        logging.debug("Get UV data function ended.")
        return process_uv_data(data)

def process_uv_data(data):
    current_uv = data["result"]["uv"]
    uv_max = data["result"]["uv_max"]
    uv_max_time_raw = data["result"]["uv_max_time"]
    utc_time = datetime.strptime(uv_max_time_raw, '%Y-%m-%dT%H:%M:%S.%fZ')
    cet_time = utc_time.replace(tzinfo=timezone.utc).astimezone(
        tz=timezone(timedelta(hours=1)))
    uv_max_time = cet_time.strftime('%H:%M')
    safe_exposure_time = data["result"]["safe_exposure_time"]["st1"]
    uv_score, uv_score_icon = determine_uv_score(current_uv)
    uv_max_score, uv_max_score_icon = determine_uv_score(uv_max)

    with open("uv.json", "w") as f:
        json.dump(data, f)
        logging.debug("UV data saved to uv.json")

    logging.debug("Get UV data function ended.")

    return uv_score_icon, current_uv, uv_max, uv_max_time, safe_exposure_time, uv_score, uv_max_score

def load_data_from_json():
    logger.info("Loading UV data from uv.json.")
    try:
        with open("uv.json", "r") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        logging.error("uv.json file not found. Unable to load UV data.")
        return None
    except Exception as e:
        logging.error(f"Error loading data from uv.json: {e}")
        return None


def get_weather_data():
    logging.debug("Get weather data (KNMI) function started.")

    knmi_url = "https://weerlive.nl/api/json-data-10min.php"

    params = {
        "key": KNMI_API_KEY,
        "locatie": KNMI_LOCATION_CODE,
    }

    try:
        response = requests.get(knmi_url, params=params, timeout=30)
        response.raise_for_status()  # Raise HTTPError for bad responses

        data = response.json()["liveweer"][0]

        weather_data_raw = response.json()

        # Collect data in JSON
        weather_data = {
            "timestamp": data['time'],
            "current_temp": data['temp'],
            "feelslike_temperature": data['gtemp'],
            "summary": data['samenv'],
            "current_humidity": data['lv'],
            "current_wind_direction": data['windr'],
            "current_wind_speed": data['windkmh'],
            "currrent_expectation": data['verw'],
            "shuruq": data['sup'],
            "maghrib": data['sunder'],
            "image": data['image'],
            "weather_today": {
                "weather_icon": data['d0weer'],
                "max_temp": data['d0tmax'],
                "min_temp": data['d0tmin'],
                "rain_chance": data['d0neerslag'],
                "sun_chance": data['d0zon']
            },
            "weather_tomorrow": {
                "weather_icon": data['d1weer'],
                "max_temp": data['d1tmax'],
                "min_temp": data['d1tmin'],
                "rain_chance": data['d1neerslag'],
                "sun_chance": data['d1zon']
            },
            "alarm_text": data['alarmtxt']
        }

        logging.debug("Get weather data (KNMI) function ended.")

        return weather_data, weather_data_raw

    except requests.RequestException as e:
        logging.error(f"First try: Error fetching data from KNMI API: {e}")
        logging.error(
            "Weather data could not be fetched. Trying again in 60 seconds.")
        time.sleep(60)

        logging.info("Trying again now..")

        try:
            response = requests.get(knmi_url, params=params, timeout=30)
            response.raise_for_status()  # Raise HTTPError for bad responses

            data = response.json()["liveweer"][0]

            # Collect data in JSON
            weather_data = {
                "timestamp": data['time'],
                "current_temp": data['temp'],
                "feelslike_temperature": data['gtemp'],
                "summary": data['samenv'],
                "current_humidity": data['lv'],
                "current_wind_direction": data['windr'],
                "current_wind_speed": data['windkmh'],
                "currrent_expectation": data['verw'],
                "shuruq": data['sup'],
                "maghrib": data['sunder'],
                "image": data['image'],
                "weather_today": {
                    "weather_icon": data['d0weer'],
                    "max_temp": data['d0tmax'],
                    "min_temp": data['d0tmin'],
                    "rain_chance": data['d0neerslag'],
                    "sun_chance": data['d0zon']
                },
                "weather_tomorrow": {
                    "weather_icon": data['d1weer'],
                    "max_temp": data['d1tmax'],
                    "min_temp": data['d1tmin'],
                    "rain_chance": data['d1neerslag'],
                    "sun_chance": data['d1zon']
                },
                "alarm_text": data['alarmtxt']
            }

            logging.debug("Get weather data (KNMI) function ended.")
            logging.info("Weather data successfully fetched the second time.")
            return weather_data
        except requests.RequestException as e:
            logging.error(f"Second try:Error fetching data from KNMI API: {e}")
            # You can handle the error in an appropriate way, for example, return default values.
            return {"Error": "Error fetching data from KNMI API",
                    "Message": str(e)}


def store_weather_data(weather_data):
    logging.debug("Store weather data (KNMI) function started.")

    json_file_path = "./weer_output.json"
    # Save the JSON response to a file
    try:
        with open(json_file_path, 'w') as json_file:
            json.dump(weather_data, json_file, indent=2)
            logging.debug("Store weather data (KNMI) function ended.")
            return True
    except IOError as e:
        logging.error(f"Error writing JSON file: {e}")
        logging.debug("Store weather data (KNMI) function ended.")
        return False


def send_weather_data(sshkey, receiving_port, receiving_server, receiving_file_path):
    logging.debug("Send weather data (KNMI) function started.")

    weather_json = f"{WEATHER_JSON_FILE_PATH}/weer_output.json"

    command = f"scp -i {sshkey} -P {receiving_port} {weather_json} {receiving_server}:{receiving_file_path}"
    logging.debug(f"Command: {command}")

    command_output = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Extract the stdout attribute
    command_stdout = command_output.stdout

    # Escape the text to prevent Telegram from interpreting it as entities
    command_stdout_escaped = html.escape(command_stdout)

    if (len(command_stdout_escaped)) < 1:
        logging.info("Data was sent successfully.")
        logging.info(f"{command_stdout_escaped}")
        logging.debug("Send weather data (KNMI) function ended.")
        return True
    else:
        logging.error(f"Error sending weather data: {command_stdout_escaped}")
        logging.debug("Send weather data (KNMI) function ended.")
        return command_stdout_escaped


def create_weather_message_summary(weather_data):
    logging.debug("Create weather message_summary function started.")

    uv_score_icon, current_uv, uv_max, uv_max_time, safe_exposure_time, uv_score, uv_max_score = get_UV_data()

    image_icon = determine_weather_icon(weather_data["image"])

    logging.debug("Create weather message_summary function started.")
    message_summary = f"""{image_icon}  ({uv_score_icon}) - <b>{weather_data["summary"]} - 🌡️ {weather_data["current_temp"]}°C - 🍃 {weather_data["current_wind_speed"]} km/u</b>

<b>Weer in het kort voor {weather_data["timestamp"]}</b>

<b>In het kort:</b>
Samenvatting: {weather_data["summary"]}
Temperatuur: {weather_data["current_temp"]}°C
Gevoelstemperatuur: {weather_data["feelslike_temperature"]}°C
UV-index: {current_uv} ({uv_score})
Max UV-index: {uv_max} ({uv_max_score}) (om {uv_max_time})
Veilige blootstellingstijd: {safe_exposure_time} min
Windrichting: {weather_data["current_wind_direction"]}
Windsnelheid: {weather_data["current_wind_speed"]} km/u
Alert: {weather_data["alarm_text"]}
"""

    logging.debug("Create weather message_summary function ended.")
    return message_summary


def create_weather_message_details(weather_data):
    uv_score_icon, current_uv, uv_max, uv_max_time, safe_exposure_time, uv_score, uv_max_score = get_UV_data()

    image_icon = determine_weather_icon(weather_data["image"])

    logging.debug("Create weather message_detail function started.")
    message_detail = f"""{image_icon} ({uv_score_icon}) - <b>{weather_data["summary"]} - 🌡️ {weather_data["current_temp"]}°C - 🍃 {weather_data["current_wind_speed"]} km/u</b>

<b>In het kort:</b>
Samenvatting: {weather_data["summary"]}
Temperatuur: {weather_data["current_temp"]}°C
UV-index: {current_uv} ({uv_score})
Veilige blootstellingstijd: {safe_exposure_time} min
Kans op regen: {weather_data["weather_today"]["rain_chance"]}%
Windrichting: {weather_data["current_wind_direction"]}
Windsnelheid: {weather_data["current_wind_speed"]} km/u
Alert: {weather_data["alarm_text"]}

<b>In detail vandaag:</b>
Gevoelstemperatuur: {weather_data["feelslike_temperature"]}°C
Verwachting: {weather_data["currrent_expectation"]}
Max temperatuur: {weather_data["weather_today"]["max_temp"]}°C
Min temperatuur: {weather_data["weather_today"]["min_temp"]}°C
Kans op regen: {weather_data["weather_today"]["rain_chance"]}%
Kans op zon: {weather_data["weather_today"]["sun_chance"]}%
Max UV-index: {uv_max} ({uv_max_score}) (om {uv_max_time})
Luchtvochtigheid: {weather_data["current_humidity"]}%
Zonsopkomst: {weather_data["shuruq"]}
Zonsondergang: {weather_data["maghrib"]}

<b>Morgen:</b>
Max temperatuur: {weather_data["weather_tomorrow"]["max_temp"]}°C
Min temperatuur: {weather_data["weather_tomorrow"]["min_temp"]}°C
Kans op regen: {weather_data["weather_tomorrow"]["rain_chance"]}%
Kans op zon: {weather_data["weather_tomorrow"]["sun_chance"]}%
"""

    logging.debug("Create weather message_detail function ended.")
    return message_detail


def determine_uv_score(current_uv):
    if current_uv <= 3:
        return "vrijwel geen", "🟩"
    elif current_uv <= 6:
        return "matig", "🟨"
    elif current_uv <= 8:
        return "sterk", "🟧"
    elif current_uv <= 11:
        return "zeer sterk", "🟥"
    elif current_uv > 11:
        return "extreem", "🟪"


def determine_weather_icon(image_string):
    if image_string == "zonnig":
        return "☀️"
    elif image_string == "bliksem":
        return "🌩️"
    elif image_string == "regen":
        return "🌧️"
    elif image_string == "buien":
        return "🌧️"
    elif image_string == "hagel":
        return "🌨️"
    elif image_string == "mist":
        return "🌫️"
    elif image_string == "sneeuw":
        return "🌨️"
    elif image_string == "bewolkt":
        return "☁️"
    elif image_string == "lichtbewolkt":
        return "🌤️"
    elif image_string == "halfbewolkt":
        return "🌥️"
    elif image_string == "halfbewolkt_regen":
        return "🌦️"
    elif image_string == "zwaarbewolkt":
        return "☁️☁️"
    elif image_string == "nachtmist":
        return "🌙🌫️"
    elif image_string == "helderenacht":
        return "🌙"
    elif image_string == "nachtbewolkt":
        return "🌙☁️"
    elif image_string == "wolkennacht":
        return "🌙☁️"
    else:
        return image_string


def send_weather_message_summary(weather_data):
    logging.debug("Send weather message summary function started.")

    with open("./users_lists/users_summary.txt", "r") as users_summary_file:
        users_summary_list = users_summary_file.read().splitlines()

    for user in users_summary_list:
        if user in AUTORIZED_USERS:
            bot.send_message(user, create_weather_message_summary(weather_data))

    logging.debug("Send weather message summary function ended.")


def send_weather_message_details(weather_data):
    logging.debug("Send weather message details function started.")

    with open("./users_lists/users_details.txt", "r") as users_details_file:
        users_details_list = users_details_file.read().splitlines()

    for user in users_details_list:
        if user in AUTORIZED_USERS:
            bot.send_message(user, create_weather_message_details(weather_data))

    logging.debug("Send weather message function ended.")


def send_error_message(message):

    error_JSON = json.dumps(message, ensure_ascii=False, indent=2)

    # Send back the formatted JSON response
    bot.send_message(CHAT_ID_PERSON_1, f"```\n{error_JSON}\n```", parse_mode='Markdown')
