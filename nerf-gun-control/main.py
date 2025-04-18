from codecs import ascii_encode
#from lib2to3.btm_matcher import BottomMatcher
from math import asin
from operator import ne
import re
import stat
import aiohttp
import asyncio
import logging
import requests
from twitchio.ext import commands
from datetime import datetime, timedelta
from reqlogger import ReqLogger
from nerf_controller import NerfController
from twitchio.errors import AuthenticationError
from params import *
import aiomysql

# Load environment variables

NEED_SUBSCRIPTION = False


class TokenManager:
    def __init__(self, access_token, refresh_token, client_id, client_secret):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret

    async def get_token(self):
        return self.access_token

    async def refresh(self):
        url = "https://id.twitch.tv/oauth2/token"
        args = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=args) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.access_token = data["access_token"]
                    if "refresh_token" in data:
                        self.refresh_token = data["refresh_token"]
                        update_vars(self.access_token, self.refresh_token)
                        print("Refresh token updated")
                    else:
                        print("No new refresh token provided")

                    return True
                else:
                    print(
                        f"Failed to refresh token: {await resp.text()} for client_id: {self.client_id}"
                    )
                    return False

    def update_bot_token(self, bot):
        bot._http.token = self.access_token
        bot.twitch_headers["Authorization"] = f"Bearer {self.access_token}"


class NerfGunBot(commands.Bot):
    def __init__(self, tokmgr=None):
        if tokmgr is None:
            self.token_manager = TokenManager(
                TWITCH_ACCESS_TOKEN, TWITCH_REFRESH_TOKEN, TWITCH_CLIENT_ID, TWITCH_SECRET
            )
        else:
            self.token_manager = tokmgr

        self.channel_names = TWITCH_CHANNEL_NAME.split(",")
        self.gun_at_home = False

        super().__init__(
            token=self.token_manager.access_token,
            client_id=self.token_manager.client_id,
            nick=self.channel_names[0],
            prefix=["!", ''],
            initial_channels=self.channel_names,
        )
        self.twitch_headers = {
            "Client-ID": self.token_manager.client_id,
            "Authorization": f"Bearer {self.token_manager.access_token}",
        }
        self.broadcaster_id = None
        self.nerf_controller = NerfController(NERF_CONTROLLER_URL)
        # Cache for follower status to minimize API calls
        self.follower_cache = {}
        # Cache timeout (5 minutes)
        self.cache_timeout = 300
        self.db = None
        self.gun_config = None
        # Gun is not at home position
        self.at_home = False
        # Add lock for gun status
        self._gun_status_lock = asyncio.Lock()
        self.gun_config = {}


    async def initialize_async(self):
        await self.connect_db()
        self.gun_config = await self.load_gun_config()
        print(f"Gun configuration: {self.gun_config}")

        # Add other initialization tasks here

    async def connect_db(self):
        self.db = await aiomysql.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            autocommit=True,
        )

    async def fetch_or_create_user_data(self, username, subscription_level):
        query = "SELECT * FROM subscribers WHERE user_id = %s"
        async with self.db.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (username,))
                user_data = await cur.fetchone()

                if user_data:
                    return user_data
                else:
                    return await self.create_new_subscriber(username, subscription_level)

    async def create_new_subscriber(self, username, subscription_level):
        new_subscriber = {
            "user_id": username,
            "subscription_level": subscription_level,
            "current_credits": self.get_initial_credits(subscription_level),
            "subscription_anniversary": datetime.utcnow().strftime("%Y-%m-%d"),
            "last_reset_date": datetime.utcnow().strftime("%Y-%m-%d"),
        }

        query = """
        INSERT INTO subscribers (user_id, subscription_level, current_credits, subscription_anniversary, last_reset_date)
        VALUES (%s, %s, %s, %s, %s)
        """

        try:
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        query,
                        (
                            new_subscriber["user_id"],
                            new_subscriber["subscription_level"],
                            new_subscriber["current_credits"],
                            new_subscriber["subscription_anniversary"],
                            new_subscriber["last_reset_date"],
                        ),
                    )
                    return new_subscriber
        except Exception as e:
            print(f"Error creating new subscriber: {e}")
            return None

    async def event_token_expired(self):
        print("Token expired, attempting to refresh...")
        success = await self.token_manager.refresh()
        if success:
            new_token = self.token_manager.access_token
            self.token_manager.update_bot_token(self)
            print("Token refreshed successfully")
            return new_token
        else:
            print("Failed to refresh token")
            return None

    async def load_gun_config(self):
        query = """
        SELECT config_key, config_value 
        FROM system_config 
        WHERE config_key IN ('min_horizontal_angle', 'max_horizontal_angle', 'min_vertical_angle', 'max_vertical_angle', 'home_x', 'home_y', 'gun_active', 'idle_timeout')
        """
        try:
            async with self.db.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query)
                    config_rows = await cur.fetchall()
                    if config_rows:
                        ret = {
                            "min_horizontal": int(
                                next(
                                    (
                                        row["config_value"]
                                        for row in config_rows
                                        if row["config_key"] == "min_horizontal_angle"
                                    ),
                                    MIN_HORIZONTAL,
                                )
                            ),
                            "max_horizontal": int(
                                next(
                                    (
                                        row["config_value"]
                                        for row in config_rows
                                        if row["config_key"] == "max_horizontal_angle"
                                    ),
                                    MAX_HORIZONTAL,
                                )
                            ),
                            "min_vertical": int(
                                next(
                                    (
                                        row["config_value"]
                                        for row in config_rows
                                        if row["config_key"] == "min_vertical_angle"
                                    ),
                                    MIN_VERTICAL,
                                )
                            ),
                            "max_vertical": int(
                                next(
                                    (
                                        row["config_value"]
                                        for row in config_rows
                                        if row["config_key"] == "max_vertical_angle"
                                    ),
                                    MAX_VERTICAL,
                                )
                            ),
                            "home_x": int(
                                next(
                                    (
                                        row["config_value"]
                                        for row in config_rows
                                        if row["config_key"] == "home_x"
                                    ),
                                    0,
                                )
                            ),
                            "home_y": int(
                                next(
                                    (
                                        row["config_value"]
                                        for row in config_rows
                                        if row["config_key"] == "home_y"
                                    ),
                                    0,
                                )
                            ),
                            "gun_active": next(
                                (
                                    row["config_value"]
                                    for row in config_rows
                                    if row["config_key"] == "gun_active"
                                ),
                                "1",
                            )
                            == "1",
                            "idle_timeout": int(
                                next(
                                    (
                                        row["config_value"]
                                        for row in config_rows
                                        if row["config_key"] == "idle_timeout"
                                    ),
                                    300,
                                )
                            ),
                        }
        except Exception as e:
            print(f"Error loading gun config from database: {e}")
            ret = {
                "min_horizontal": MIN_HORIZONTAL,
                "max_horizontal": MAX_HORIZONTAL,
                "min_vertical": MIN_VERTICAL,
                "max_vertical": MAX_VERTICAL,
                "home_x": 0,
                "home_y": 0,
                "gun_active": True,
                "idle_timeout": 300,
            }
        finally:
            print(f"Got config:\m{ret}")
            return ret

    async def event_ready(self):
        print(f"Logged in as | {self.nick}")
        # FIXME:  need to handle multiple channels
        self.broadcaster_id = await self.get_user_id(self.channel_names[0])

    async def event_message(self, message):
        if message.echo:
            return
        await self.handle_commands(message)

        # Custom handling for the compact command format
        content = message.content.strip()
        
        # Match patterns like !!5,6,7 or !f5,6,7 or !fire5,6,7
        compact_fire_match = re.match(r'^!(!|f|fire)(\d+),(\d+),(\d+)$', content)
        if compact_fire_match:
            cmd_alias, x_str, y_str, z_str = compact_fire_match.groups()
            try:
                x = int(x_str)
                y = int(y_str)
                z = int(z_str)
                await self.do_fire_command(message.author, message, message.channel, x, y, z)
            except ValueError:
                await message.channel.send("Invalid parameters. Please use numbers for angles and shots.") 

        return    

    async def check_follower_status(self, user_id: str, broadcaster_id: str) -> bool:
        """Check if a user is following the channel, with caching"""
        cache_key = f"{user_id}_{broadcaster_id}"

        print(f"Checking follower status for {cache_key}...")
        # Check cache first
        if False and (cache_key in self.follower_cache):
            cached_data = self.follower_cache[cache_key]
            if datetime.now() - cached_data["timestamp"] < timedelta(seconds=self.cache_timeout):
                return cached_data["is_following"]

        try:
            # Use TwitchIO's built-in method
            print("Sending get_channel_followers request")
            followers = await self._http.get_channel_followers(
                token=self.token_manager.access_token,
                broadcaster_id=broadcaster_id,
                user_id=int(user_id),
            )

            is_following = len(followers) > 0

            # Update cache
            self.follower_cache[cache_key] = {
                "is_following": is_following,
                "timestamp": datetime.now(),
            }

            return is_following

        except Exception as e:
            print(f"Error checking follower status: {e}")
            return False


    @commands.command(name='fire', aliases=['f', '!'])
    async def fire_command(self, ctx: commands.Context, *, args_str=""):
        # Process standard space-separated arguments
        args = args_str.replace(',', ' ').split()
        
        if len(args) >= 3:
            try:
                x, y, z = int(args[0]), int(args[1]), int(args[2])
                await self.do_fire_command(ctx.author, ctx.message, ctx.channel, x, y, z)
                return
            except (ValueError, IndexError):
                pass
        
        await ctx.send("Usage: !fire 30 45 2  or  !f 30,45,2  or  !!30,45,2")

 
    async def do_fire_command(self, author, message, channel, x: int, y: int, z: int):
        if not await self.get_gun_status():
            await channel.send("The Nerf gun is currently disabled.")
            return

        username = author.name
        bcaster_id = message.tags.get("room-id")

        # Check angle limits
        if (
            x < self.gun_config["min_horizontal"]
            or x > self.gun_config["max_horizontal"]
            or y < self.gun_config["min_vertical"]
            or y > self.gun_config["max_vertical"]
        ):
            await channel.send(
                f"Fire command out of bounds. Horizontal: {self.gun_config['min_horizontal']} to {self.gun_config['max_horizontal']}, "
                f"Vertical: {self.gun_config['min_vertical']} to {self.gun_config['max_vertical']}"
            )
            return

        # Check if user is subscribed
        # FIXME:  temporarily fail owner check and force follower and subscriber checking
        channel_owner = True and (username in self.channel_names)
        if not channel_owner:

            # Check if follower verification is required
            # FIXME:  Temporary force identity check
            if True or config.get("follower_required") == "1":
                # Get channel ID from the context
                # channel_id = ctx.channel.id
                is_following = await self.check_follower_status(str(author.id), bcaster_id)
                # followers = await self.fetch_users(broadcaster_id = self.broadcaster_id)
                # print(followers)

                if not is_following:
                    await channel.send(
                        f"@{author.name}, you need to be a follower to use the Nerf gun! Follow the channel and try again."
                    )
                    return

                if NEED_SUBSCRIPTION:
                    if not await self.check_subscription(author):
                        await channel.send(
                            f"{username} is not a subscriber and cannot use the !fire command."
                        )
                        await channel.send(f"/w {username} you are not a subscriber")
                        return

                    subscription_level = await self.get_subscription_level(ctx.author)
                    user_data = await self.fetch_or_create_user_data(username, subscription_level)
                else:
                    subscription_level = 0
                    user_data = await self.fetch_or_create_user_data(username, subscription_level)

                if user_data is None:
                    await channel.send(f"Failed to fetch or create data for {username}.")
                    return

                current_credits = user_data["current_credits"]
                credits_per_shot = self.get_credits_per_shot(subscription_level)

                total_cost = credits_per_shot * z
                if current_credits < total_cost:
                    await channel.send(
                        f"{username} doesn't have enough credits. Required: {total_cost}, Available: {current_credits}"
                    )
                    return

                # Perform the fire action
                shots_fired = await self.do_fire(x, y, z)

                if shots_fired >= 0:
                    # Update user credits
                    credits_used = shots_fired * credits_per_shot
                    remaining_credits = current_credits - credits_used
                    await self.update_user_credits(username, remaining_credits)
        else:
            # Perform the fire action
            print("Channel owner, firing without credits")
            shots_fired = await self.do_fire(x, y, z)
            remaining_credits = "unlimited"

        if shots_fired >= 0:
            # Send messages
            await channel.send(f"{username} fired {shots_fired} shots!")
            await author.send(f"You have {remaining_credits} credits remaining.")
        else:
            await channel.send("Error shooting... Gun INACTIVE")

    async def old_check_subscription(self, user):

        #        with ReqLogger(logging.DEBUG):
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

    async def check_subscription(self, user):

        #        with ReqLogger(logging.DEBUG):
        user_id = await self.get_user_id(user.name)
        # url = f"https://api.twitch.tv/helix/subscriptions/user?broadcaster_id={self.broadcaster_id}&user_id={user_id}"

        try:
            subs = await self._http.get_channel_subscriptions(
                token=self.token_manager.access_token,
                broadcaster_id=self.broadcaster_id,
                user_ids=[user_id],
            )
            if subs:
                return True

            return False
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

    async def old_get_user_id(self, username):

        url = f"https://api.twitch.tv/helix/users?login={username}"

        try:
            response = requests.get(url, headers=self.twitch_headers)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["id"]
        except requests.RequestException as e:
            print(f"Error getting user ID: {e}")
            return None

    async def get_user_id(self, username):
        try:
            users = await self.fetch_users(names=[username])
            return users[0].id
        except requests.RequestException as e:
            print(f"Error getting user ID: {e}")
            return None

    def get_initial_credits(self, subscription_level):
        credits = {0: 5, 1: 100, 2: 200, 3: 300}
        return credits.get(subscription_level, 5)

    def get_credits_per_shot(self, subscription_level):
        credits = {0: 1, 1: 10, 2: 8, 3: 6}
        return credits.get(subscription_level, 1)

    async def _watchdog_monitor(self):
        WATCHDOG_TIMEOUT = self.gun_config.get("idle_timeout", 300)
        SLEEP_TIMEOUT = 5
        while True:
            if await self.get_gun_status():
                await asyncio.sleep(SLEEP_TIMEOUT)
                async with self._lock:
                    if not self.gun_at_home:
                        continue
                    if (datetime.now() - self._last_shot_time).total_seconds() >= WATCHDOG_TIMEOUT:
                        await self.return_to_home()
            else:
                await asyncio.sleep(SLEEP_TIMEOUT)
                await self.check_gun_status()

    def return_to_home(self):
        if not self.at_home and self.gun_config["gun_active"]:
            self.at_home = True
            self.nerf_controller.fire(
                self.gun_config["home_x"], self.gun_config["home_y"], 0, False
            )

    async def update_last_shot(self):
        async with self._lock:
            self._last_shot_time = datetime.now()

    async def update_gun_status(self, status):
        query = """
        UPDATE system_config 
        SET config_value = %s
        WHERE config_key = 'gun_active'
        """

        try:
            async with self.db.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, (1 if status else 0,))
                    await conn.commit()
                    await self.set_gun_status(status)  # Update local config with lock
                    return True
        except Exception as e:
            print(f"Error updating gun status: {e}")
            return False

    async def check_gun_status(self):
        query = """
        SELECT config_value 
        FROM system_config 
        WHERE config_key = 'gun_active'
        """
        try:
            async with self.db.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query)
                    result = await cursor.fetchone()
                    if result:
                        status = bool(int(result[0]))
                        await self.set_gun_status(status)  # Update local config with lock
                        return status
                    return False
        except Exception as e:
            print(f"Error checking gun status: {e}")
            return False

    async def kill_watchdog(self):
        """Stop the watchdog monitoring task"""
        if hasattr(self, "_watchdog_task"):
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
            delattr(self, "_watchdog_task")
            delattr(self, "_last_shot_time")
            delattr(self, "_lock")

    async def do_fire(self, x, y, z):
        # This function should communicate with the GUNCTRL system
        # Reset watchdog timer on each shot
        if not hasattr(self, "_last_shot_time"):
            self._lock = asyncio.Lock()
            self._last_shot_time = datetime.now()
            self._watchdog_task = asyncio.create_task(self._watchdog_monitor())

        asyncio.create_task(self.update_last_shot())

        # Perform the actual firing
        if not await self.check_gun_status():
            return -1

        print(f"Firing: x={x}, y={y}, z={z}")
        ok, status = self.nerf_controller.fire(x, y, z, wait=True)
        if not ok:
            print(f"Error: {status}")
            await self.update_gun_status(False)
            return status.get("shots", 0) # Return the number of shots fired

        return status.get("shots", 0)

    async def update_user_credits(self, user_id, new_credits):
        query = """
        UPDATE subscribers
        SET current_credits = %s
        WHERE user_id = %s
        """

        try:
            async with self.db.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, (new_credits, user_id))
                    await conn.commit()  # Commit the transaction
                    return True
        except Exception as e:
            print(f"Error updating user credits: {e}")
            return False

    async def wp_update_user_credits(self, username, new_credits):
        try:
            requests.put(
                f"{WORDPRESS_API_URL}/subscribers?user_id={username}",
                json={"current_credits": new_credits},
            )
        except requests.RequestException as e:
            print(f"Error updating user credits: {e}")

    async def wp_fetch_or_create_user_data(self, username, subscription_level):
        try:
            response = requests.get(f"{WORDPRESS_API_URL}/subscribers?user_id={username}")
            users = response.json()

            if users:
                return users[0]
            else:
                return await self.wp_create_new_subscriber(username, subscription_level)
        except requests.RequestException as e:
            print(f"Error fetching user data: {e}")
            return None

    async def wp_create_new_subscriber(self, username, subscription_level):
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

    def wp_load_gun_config(self):
        if WORDPRESS_API_URL:
            try:
                response = requests.get(f"{WORDPRESS_API_URL}/config")
                return response.json()
            except requests.RequestException as e:
                print(f"Error loading gun config: {e}")

        print("Using default gun configuration")
        return {
            "min_horizontal": MIN_HORIZONTAL,
            "max_horizontal": MAX_HORIZONTAL,
            "min_vertical": MIN_VERTICAL,
            "max_vertical": MAX_VERTICAL,
        }

    async def get_gun_status(self):
        """Get gun active status with synchronization"""
        async with self._gun_status_lock:
            return self.gun_config.get("gun_active", False)

    async def set_gun_status(self, status: bool):
        """Set gun active status with synchronization"""
        async with self._gun_status_lock:
            self.gun_config["gun_active"] = status


async def main():
    bot = NerfGunBot()
    await bot.initialize_async()
    try:
        await bot.start()
    except AuthenticationError:
        print("Authentication failed. Attempting to refresh token...")
        new_token = await bot.token_manager.refresh()
        if new_token:
            bot.token_manager.update_bot_token(bot)
            bot.kill_watchdog()
            print("Token refreshed. Restarting bot...")
            bot = NerfGunBot(
                tokmgr=bot.token_manager
            )  # Create a new bot instance with the updated token
            await bot.initialize_async()
            await bot.start()
        else:
            print("Failed to refresh token. Please check your Twitch credentials.")
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"BOT Client Id: {TWITCH_CLIENT_ID}")
    finally:
        await bot.close()


if __name__ == "__main__":
    with ReqLogger(level=logging.DEBUG):
        asyncio.run(main())
