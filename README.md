# Dutch Weather Telegram bot

This project is an addition to my Nest Project, but works as a standalone as well. Simply remove the functions you don't want. In essence it retrieves several weather data and sends it to your Telegram account. It also stores the data in a JSON file and sends it to another server (in my case where my Nest Project is hosted).

## Features
### Interactive Commands:
- /start - Initiates the bot and provides a welcome message.
- /menu - Displays the menu with available weather options.
- Weather Summaries: Provides a concise summary of current weather conditions, including temperature, wind speed, and a brief description.
- Detailed Weather Information: Offers detailed weather data, including temperature, humidity, wind direction and speed, UV index, sunrise and sunset times, and forecasts for today and tomorrow.
- Authorized Access: Ensures that only authorized users can access the bot’s functionalities.
- Automatic Logging: Logs weather data twice per hour and more detailed data a few times per day.
- Weather Data Retrieval: Fetches weather data from the KNMI API and handles potential errors and retries.
- UV Data Retrieval: Obtains UV index data from the OpenUV API, with support for both primary and backup API keys.
- Data Processing: Processes raw weather and UV data to create user-friendly summaries and detailed reports.
- Data Transmission: Securely transmits weather data to a designated server using SCP.
- Scheduled Updates: Supports scheduling of regular weather updates using the schedule module.

## Files
`weather_bot.py`: The main script. \
`weather_functions.py`: Functions used in the script. \
`weather_update.py`: The weather update function. \
`.env.example`: An example `.env` file. \
`weather_bot.service`: A systemd service file. \
`weather_update.service`: A systemd service file.

## Setup

### Prerequisites
- Python 3.x
- `pip` package manager
- A Telegram bot token. You can get one by creating a bot through the [BotFather](https://core.telegram.org/bots#botfather).
- API keys for the OpenUV and KNMI APIs
- Encryption key. [Check documentation how to get one](https://cryptography.io/en/latest/fernet/).

### Installation

1. **Clone the repository:**
    ```bash
    git clone https://github.com/MadeByAdem/WeerBot
    cd archive_bot
    ```

2. **Create a virtual environment and activate it:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Set up your environment variables:**

    Copy the `.env.example` file to `.env` and variables with your keys.
    ```bash
    cp .env.example .env
    ```

5. **Run the bot:**
    ```bash
    python weather_bot.py
    ```

### Setting up as a Systemd Service

1. **Modify the service files:**

    Update the `weather_bot.service` file with your actual paths:
    ```ini
    [Unit]
    Description=Weather Bot
    After=network.target

    [Service]
    ExecStart=/your/path/to/weather_bot/venv/bin/python /your/path/to/weather_bot/weather_bot.py
    WorkingDirectory=/your/path/to/weather_bot
    User=root
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

    Update the `weather_update.service` file with your actual paths:
    ```ini
    [Unit]
    Description=Weather Update
    After=network.target

    [Service]
    ExecStart=/your/path/to/weather_bot/venv/bin/python /your/path/to/weather_bot/weather_update.py
    WorkingDirectory=/your/path/to/weather_bot
    User=root
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

2. **Copy the service file to systemd:**
    ```bash
    sudo cp weather_bot.service /etc/systemd/system/
    sudo cp weather_update.service /etc/systemd/system/
    ```

3. **Reload systemd and start the service:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl start weather_bot.service
    sudo systemctl start weather_update.service
    ```

4. **Enable the service to start on boot:**
    ```bash
    sudo systemctl enable weather_bot.service
    sudo systemctl enable weather_update.service
    ```

## Usage
1. Start a chat with your bot on Telegram.
2. Use the `/start` command to receive the welcome message.
3. Use the `/menu` command to see the available weather options.

## Environment Variables
`SECRET_TOKEN_WEATHERBOT` : Your Telegram bot token. \
`CHAT_ID_PERSON_1` : Chat ID of the first person. \
`CHAT_ID_PERSON_2` : Chat ID of the second person. You can add more, just modify the functions. \
`SSHKEY` : If you want to send the json to another server. Make sure this sshkey is added to the receiving server. \
`RECEIVING_SERVER` : The IP address and port of the receiving server. \
`RECEIVING_FILE_PATH` : The path on the receiving server where the data should be stored. \
`LOG_DIRECTORY` : The directory where the log file is stored. \
`LOG_FILE_NAME` : The name of the log file. \
`KNMI_API_KEY` : Your KNMI API key. \
`KNMI_LOCATION_CODE` : The location you want to receive data from (format: `latitude,longitude`). \
`WEATHER_JSON_FILE_PATH` : The path where the json file is stored. \
`UV_API_KEY` : Your OpenUV API key. \
`UV_API_BACKUP_KEY` : Your OpenUV backup API key (in case of to many api requests)  \
`ENCRYPTION_KEY` : Your encryption key \


## Contributing
Feel free to submit issues or pull requests if you have suggestions for improvements or new features. Please follow the existing coding style.

## License
This project is licensed under the Custom License. See the [LICENSE](LICENSE) file for more details.