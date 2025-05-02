import os, dotenv
from tkinter import NO
from weakref import ref




WITH_TTG_1 = True
WORDPRESS_API_URL = None
NERF_CONTROLLER_URL = None
MIN_HORIZONTAL = None
MAX_HORIZONTAL = None
MIN_VERTICAL = None
MAX_VERTICAL = None

TWITCH_CHANNEL_NAME = None
TWITCH_ACCESS_TOKEN = None
TWITCH_CLIENT_ID = None
TWITCH_SECRET = None
TWITCH_REFRESH_TOKEN = None
APP_ACCESS_TOKEN = None

DB_HOST = None
DB_USER = None
DB_PASSWORD = None
DB_NAME = None
DB_PORT = None

# OBS Integration
OBS_MESSAGE_LOG_FILE = None


# Configuration
def load_vars():
    global WORDPRESS_API_URL,NERF_CONTROLLER_URL
    global MAX_HORIZONTAL,MAX_VERTICAL,MIN_HORIZONTAL,MIN_VERTICAL
    global TWITCH_CHANNEL_NAME, TWITCH_ACCESS_TOKEN, TWITCH_REFRESH_TOKEN
    global TWITCH_CLIENT_ID, TWITCH_SECRET
    global APP_ACCESS_TOKEN
    global DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT
    global OBS_MESSAGE_LOG_FILE

    dotenv.load_dotenv(override=True)

    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME")

    WORDPRESS_API_URL = os.getenv("WORDPRESS_API_URL")
    NERF_CONTROLLER_URL = os.getenv("NERF_CONTROLLER_URL", "http://localhost:5555")
    MIN_HORIZONTAL = int(os.getenv("MIN_HORIZONTAL", -45))
    MAX_HORIZONTAL = int(os.getenv("MAX_HORIZONTAL", 45))
    MIN_VERTICAL = int(os.getenv("MIN_VERTICAL", 0))
    MAX_VERTICAL = int(os.getenv("MAX_VERTICAL", 60))


    TWITCH_CHANNEL_NAME = os.getenv("TWITCH_CHANNEL_NAME")
    TWITCH_ACCESS_TOKEN = os.getenv("BOT_USER_ACCESS_TOKEN")
    TWITCH_CLIENT_ID = os.getenv("BOT_CLIENT_ID")
    TWITCH_SECRET = os.getenv("BOT_CLIENT_SECRET")
    TWITCH_REFRESH_TOKEN = os.getenv("BOT_USER_REFRESH_TOKEN")
    APP_ACCESS_TOKEN = os.getenv("BOT_APP_ACCESS_TOKEN")
    
    # OBS Integration
    OBS_MESSAGE_LOG_FILE = os.getenv('OBS_MESSAGE_LOG_FILE', '/Users/vadim/work/nerf/obs-messages.txt')
    pass





def update_vars(access_token, refresh_token):
    with open(".env", "a") as f:
        f.write(f"\nBOT_USER_ACCESS_TOKEN={access_token}\n")
        f.write(f"BOT_USER_REFRESH_TOKEN={refresh_token}\n")

    global TWITCH_ACCESS_TOKEN
    global TWITCH_REFRESH_TOKEN
    TWITCH_ACCESS_TOKEN = access_token
    TWITCH_REFRESH_TOKEN = refresh_token


def update_app_token(app_access_token):
    global APP_ACCESS_TOKEN

    with open(".env", "a") as f:
        f.write(f"\nBOT_APP_ACCESS_TOKEN={app_access_token}\n")

    APP_ACCESS_TOKEN = app_access_token



load_vars()



