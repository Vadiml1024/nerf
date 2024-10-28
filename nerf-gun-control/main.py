from hmac import new
from lib2to3.btm_matcher import BottomMatcher
from operator import ne
import aiohttp
import os
from pydoc import cli
import sys
import asyncio
import logging
import requests
from twitchio.ext import commands
from datetime import datetime
from reqlogger import ReqLogger
from nerf_controller import NerfController
from twitchio.errors import AuthenticationError
from params import *

# Load environment variables



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
            "client_secret": self.client_secret
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=args) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.access_token = data['access_token']
                    if 'refresh_token' in data:
                        self.refresh_token = data['refresh_token']
                        update_vars(self.access_token, self.refresh_token)
                        print("Refresh token updated")
                    else:
                        print("No new refresh token provided")
                   
                    return True
                else:
                    print(f"Failed to refresh token: {await resp.text()}")
                    return False

    def update_bot_token(self, bot):
        bot._http.token = self.access_token
        bot.twitch_headers["Authorization"] = f"Bearer {self.access_token}"

class NerfGunBot(commands.Bot):
    def __init__(self, tokmgr = None):
        if tokmgr is None:
                self.token_manager = TokenManager(
                TWITCH_ACCESS_TOKEN,
                TWITCH_REFRESH_TOKEN,
                TWITCH_CLIENT_ID,
                TWITCH_SECRET
            )
        else:
            self.token_manager = tokmgr

        super().__init__(
                token=self.token_manager.access_token,
                client_id=self.token_manager.client_id,
                nick=TWITCH_CHANNEL_NAME,
                prefix="!",
                initial_channels=[TWITCH_CHANNEL_NAME]
            )
        self.twitch_headers = {
            "Client-ID": self.token_manager.client_id,
            "Authorization": f"Bearer {self.token_manager.access_token}",
        }
        self.broadcaster_id = None
        self.nerf_controller = NerfController(NERF_CONTROLLER_URL)
        self.gun_config = self.load_gun_config()
        # Cache for follower status to minimize API calls
        self.follower_cache = {}
        # Cache timeout (5 minutes)
        self.cache_timeout = 300
         

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
    

    def load_gun_config(self):
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

    async def event_ready(self):
        print(f"Logged in as | {self.nick}")
        self.broadcaster_id = await self.get_user_id(TWITCH_CHANNEL_NAME)

    async def event_message(self, message):
        if message.echo:
            return
        await self.handle_commands(message)

    async def check_follower_status(self, user_id: str, broadcaster_id: str) -> bool:
        """Check if a user is following the channel, with caching"""
        cache_key = f"{user_id}_{broadcaster_id}"
        
        print(f"Checking follower status for {cache_key}...")
        # Check cache first
        if cache_key in self.follower_cache:
            cached_data = self.follower_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self.cache_timeout):
                return cached_data['is_following']
        
        try:
            # Use TwitchIO's built-in method
            print("Sending get_channel_followers request")
            followers = await self._http.get_channel_followers(token = self.token_manager.access_token,
                                                               broadcaster_id=broadcaster_id, 
                                                               user_id=int(user_id))
            is_following = len(followers.data) > 0
            
            # Update cache
            self.follower_cache[cache_key] = {
                'is_following': is_following,
                'timestamp': datetime.now()
            }
            
            return is_following
            
        except Exception as e:
            print(f"Error checking follower status: {e}")
            return False
        

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
        channel_owner = False and username == TWITCH_CHANNEL_NAME
        if not channel_owner:
        

        # Check if follower verification is required
            if True or config.get('follower_required') == '1':
                # Get channel ID from the context
                # channel_id = ctx.channel.id
                is_following = await self.check_follower_status(str(ctx.author.id), self.broadcaster_id)
                
                if not is_following:
                    await ctx.send(f"@{ctx.author.name}, you need to be a follower to use the Nerf gun! Follow the channel and try again.")
                    return

                if not await self.check_subscription(ctx.author):
                    await ctx.send(f"{username} is not a subscriber and cannot use the !fire command.")
                    await ctx.send(f"/w {username} you are not a subscriber")
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
        else:
            # Perform the fire action
            shots_fired = self.do_fire(x, y, z)
            remaining_credits = 'unlimited'

        # Send messages
        await ctx.send(f"{username} fired {shots_fired} shots!")
        await ctx.send(f"/w {username} You have {remaining_credits} credits remaining.")

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
                subs = await self._http.get_channel_subscriptions(token = self.token_manager.access_token, 
                                                            broadcaster_id=self.broadcaster_id,user_ids=[user_id])
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
            users = await self.fetch_users(names=[ username ])
            return users[0].id
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


       
async def main():
    bot = NerfGunBot()
    try:
        await bot.start()
    except AuthenticationError:
        print("Authentication failed. Attempting to refresh token...")
        new_token = await bot.token_manager.refresh()
        if new_token:
            bot.token_manager.update_bot_token(bot)
            print("Token refreshed. Restarting bot...")
            bot = NerfGunBot(tokmgr=bot.token_manager)  # Create a new bot instance with the updated token
            await bot.start()
        else:
            print("Failed to refresh token. Please check your Twitch credentials.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    with ReqLogger(level=logging.DEBUG):
        asyncio.run(main())