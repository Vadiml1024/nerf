import os, dotenv

dotenv.load_dotenv()


# Configuration
WORDPRESS_API_URL = os.getenv("WORDPRESS_API_URL")
MIN_HORIZONTAL = int(os.getenv("MIN_HORIZONTAL", -45))
MAX_HORIZONTAL = int(os.getenv("MAX_HORIZONTAL", 45))
MIN_VERTICAL = int(os.getenv("MIN_VERTICAL", 0))
MAX_VERTICAL = int(os.getenv("MAX_VERTICAL", 60))


TWITCH_CHANNEL_NAME = os.getenv("TWITCH_CHANNEL_NAME")
WITH_TTG_1 = True

if WITH_TTG_1:
    TWITCH_ACCESS_TOKEN = os.getenv("TTG_ACCESS_TOKEN")
    TWITCH_CLIENT_ID = os.getenv("TTG_TWITCH_BOT_CLIENT_ID")
    TWITCH_SECRET = os.getenv("TTG_TWITCH_BOT_CLIENT_SECRET")
    TWITCH_REFRESH_TOKEN = os.getenv("TTG_REFRESH_TOKEN")

