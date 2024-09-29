import os
from dotenv import load_dotenv
import requests
import json
from twitchio.ext import commands
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
WORDPRESS_API_URL = os.getenv("WORDPRESS_API_URL")
MIN_HORIZONTAL = int(os.getenv("MIN_HORIZONTAL", -45))
MAX_HORIZONTAL = int(os.getenv("MAX_HORIZONTAL", 45))
MIN_VERTICAL = int(os.getenv("MIN_VERTICAL", 0))
MAX_VERTICAL = int(os.getenv("MAX_VERTICAL", 60))

# Twitch configuration
TWITCH_OAUTH_TOKEN = os.getenv("TWITCH_OAUTH_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CHANNEL_NAME = os.getenv("TWITCH_CHANNEL_NAME")


class NerfGunBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TWITCH_OAUTH_TOKEN, prefix="!", initial_channels=[TWITCH_CHANNEL_NAME]
        )
        self.gun_config = self.load_gun_config()
        self.twitch_headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {TWITCH_OAUTH_TOKEN}",
        }
        self.broadcaster_id = None

    async def event_ready(self):
        print(f"Logged in as | {self.nick}")
        self.broadcaster_id = await self.get_user_id(TWITCH_CHANNEL_NAME)

    async def event_message(self, message):
        if message.echo:
            return
        await self.handle_commands(message)

    def load_gun_config(self):
        try:
            response = requests.get(f"{WORDPRESS_API_URL}/config")
            return response.json()
        except requests.RequestException as e:
            print(f"Error loading gun config: {e}")
            return {
                "min_horizontal": MIN_HORIZONTAL,
                "max_horizontal": MAX_HORIZONTAL,
                "min_vertical": MIN_VERTICAL,
                "max_vertical": MAX_VERTICAL,
            }

    @commands.command(name="fire")
    async def fire_command(self, ctx: commands.Context, x: int, y: int, z: int):
        username = ctx.author.name

        # Check angle limits
        if (
            x < self.gun_config["min_horizontal"]
            or x > self.gun_config["max_horizontal"]
            or y < self.gun_config["min_vertical"]
            or y > self.gun_config["max_vertical"]
        ):
            await ctx.send(
                f"Fire command out of bounds. Horizontal: {self.gun_config['min_horizontal']} to {self.gun_config['max_horizontal']}, "
                f"Vertical: {self.gun_config['min_vertical']} to {self.gun_config['max_vertical']}"
            )
            return

        # Check if user is subscribed
        if not await self.check_subscription(ctx.author):
            await ctx.send(f"{username} is not a subscriber and cannot use the !fire command.")
            return

        subscription_level = await self.get_subscription_level(ctx.author)
        user_data = await self.fetch_or_create_user_data(username, subscription_level)

        if user_data is None:
            await ctx.send(f"Failed to fetch or create data for {username}.")
            return

        current_credits = user_data["current_credits"]
        credits_per_shot = self.get_credits_per_shot(subscription_level)

        total_cost = credits_per_shot * z
        if current_credits < total_cost:
            await ctx.send(
                f"{username} doesn't have enough credits. Required: {total_cost}, Available: {current_credits}"
            )
            return

        # Perform the fire action
        shots_fired = self.do_fire(x, y, z)

        # Update user credits
        credits_used = shots_fired * credits_per_shot
        remaining_credits = current_credits - credits_used
        await self.update_user_credits(username, remaining_credits)

        # Send messages
        await ctx.send(f"{username} fired {shots_fired} shots!")
        await ctx.send(f"/w {username} You have {remaining_credits} credits remaining.")

    async def check_subscription(self, user):
        user_id = await self.get_user_id(user.name)
        url = f"https://api.twitch.tv/helix/subscriptions/user?broadcaster_id={self.broadcaster_id}&user_id={user_id}"

        try:
            response = requests.get(url, headers=self.twitch_headers)
            response.raise_for_status()
            data = response.json()
            return len(data["data"]) > 0
        except requests.RequestException as e:
            print(f"Error checking subscription: {e}")
            return False

    async def get_subscription_level(self, user):
        user_id = await self.get_user_id(user.name)
        url = f"https://api.twitch.tv/helix/subscriptions/user?broadcaster_id={self.broadcaster_id}&user_id={user_id}"

        try:
            response = requests.get(url, headers=self.twitch_headers)
            response.raise_for_status()
            data = response.json()

            if not data["data"]:
                return 0  # Not subscribed

            tier = data["data"][0]["tier"]
            return tier // 1000  # Convert tier (1000, 2000, 3000) to level (1, 2, 3)
        except requests.RequestException as e:
            print(f"Error getting subscription level: {e}")
            return 0

    async def get_user_id(self, username):
        url = f"https://api.twitch.tv/helix/users?login={username}"

        try:
            response = requests.get(url, headers=self.twitch_headers)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["id"]
        except requests.RequestException as e:
            print(f"Error getting user ID: {e}")
            return None

    async def fetch_or_create_user_data(self, username, subscription_level):
        try:
            response = requests.get(f"{WORDPRESS_API_URL}/subscribers?user_id={username}")
            users = response.json()

            if users:
                return users[0]
            else:
                return await self.create_new_subscriber(username, subscription_level)
        except requests.RequestException as e:
            print(f"Error fetching user data: {e}")
            return None

    async def create_new_subscriber(self, username, subscription_level):
        new_subscriber = {
            "user_id": username,
            "subscription_level": subscription_level,
            "current_credits": self.get_initial_credits(subscription_level),
            "subscription_anniversary": datetime.utcnow().strftime("%Y-%m-%d"),
        }

        try:
            response = requests.post(f"{WORDPRESS_API_URL}/subscribers", json=new_subscriber)
            return response.json()
        except requests.RequestException as e:
            print(f"Error creating new subscriber: {e}")
            return None

    def get_initial_credits(self, subscription_level):
        credits = {1: 100, 2: 200, 3: 300}
        return credits.get(subscription_level, 100)

    def get_credits_per_shot(self, subscription_level):
        credits = {1: 10, 2: 8, 3: 6}
        return credits.get(subscription_level, 10)

    def do_fire(self, x, y, z):
        # This function should communicate with the GUNCTRL system
        # For now, we'll just print the firing details and return the number of shots
        print(f"Firing: x={x}, y={y}, z={z}")
        return z

    async def update_user_credits(self, username, new_credits):
        try:
            requests.put(
                f"{WORDPRESS_API_URL}/subscribers?user_id={username}",
                json={"current_credits": new_credits},
            )
        except requests.RequestException as e:
            print(f"Error updating user credits: {e}")


def main():
    bot = NerfGunBot()
    bot.run()


if __name__ == "__main__":
    main()
