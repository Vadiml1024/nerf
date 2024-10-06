import os, dotenv
from weakref import ref




WITH_TTG_1 = True
WORDPRESS_API_URL = None
MIN_HORIZONTAL = None
MAX_HORIZONTAL = None
MIN_VERTICAL = None
MAX_VERTICAL = None

TWITCH_CHANNEL_NAME = None
TWITCH_ACCESS_TOKEN = None
TWITCH_CLIENT_ID = None
TWITCH_SECRET = None
TWITCH_REFRESH_TOKEN = None


# Configuration
def load_vars():
    global WORDPRESS_API_URL
    global MAX_HORIZONTAL,MAX_VERTICAL,MIN_HORIZONTAL,MIN_VERTICAL
    global TWITCH_CHANNEL_NAME, TWITCH_ACCESS_TOKEN, TWITCH_REFRESH_TOKEN
    global TWITCH_CLIENT_ID, TWITCH_SECRET

    WORDPRESS_API_URL = os.getenv("WORDPRESS_API_URL")
    MIN_HORIZONTAL = int(os.getenv("MIN_HORIZONTAL", -45))
    MAX_HORIZONTAL = int(os.getenv("MAX_HORIZONTAL", 45))
    MIN_VERTICAL = int(os.getenv("MIN_VERTICAL", 0))
    MAX_VERTICAL = int(os.getenv("MAX_VERTICAL", 60))


    TWITCH_CHANNEL_NAME = os.getenv("TWITCH_CHANNEL_NAME")
    TWITCH_ACCESS_TOKEN = os.getenv("TTG_ACCESS_TOKEN")
    TWITCH_CLIENT_ID = os.getenv("TTG_TWITCH_BOT_CLIENT_ID")
    TWITCH_SECRET = os.getenv("TTG_TWITCH_BOT_CLIENT_SECRET")
    TWITCH_REFRESH_TOKEN = os.getenv("TTG_REFRESH_TOKEN")


def load_vars():
    dotenv.load_dotenv(override=True)


def update_vars(access_token, refresh_token):
    with open(".env", "a") as f:
        f.write(f"\nTTG_ACCESS_TOKEN={access_token}\n")
        f.write(f"TTG_REFRESH_TOKEN={refresh_token}\n")
    
    global TWITCH_ACCESS_TOKEN
    global TWITCH_REFRESH_TOKEN
    TWITCH_ACCESS_TOKEN = access_token
    TWITCH_REFRESH_TOKEN = refresh_token


load_vars()



