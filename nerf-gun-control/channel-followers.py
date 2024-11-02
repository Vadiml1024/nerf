from json import load
from operator import le
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from twitchAPI.helper import first
import asyncio
from dotenv import load_dotenv
import os

load_dotenv('.env', override=True)
CLIENT_ID = os.getenv('BOT_CLIENT_ID')
CLIENT_SECRET = os.getenv('BOT_CLIENT_SECRET')

async def main():
    import sys

    login_name = sys.argv[1] if (len(sys.argv) > 1) else 'vadiml1024'
    # Initialize the Twitch instance
    twitch = await Twitch(CLIENT_ID, CLIENT_SECRET)

    # Define the required scope
    target_scope = [
                    AuthScope.MODERATOR_READ_FOLLOWERS,
                    AuthScope.CHAT_EDIT, AuthScope.CHAT_READ,
                    AuthScope.WHISPERS_EDIT, AuthScope.WHISPERS_READ
                    ]

    # Set up the user authenticator
    auth = UserAuthenticator(twitch, target_scope, force_verify=False)

    # Authenticate and set the user authentication
    token, refresh_token = await auth.authenticate()
    await twitch.set_user_authentication(token, target_scope, refresh_token)

    print(f"token={token}\nrefresh={refresh_token}\n")

    with open(".env", "a") as f:
        f.write(f"\nBOT_USER_ACCESS_TOKEN={token}\n\BOT_USER_REFRESH_TOKEN={refresh_token}\n")
    
    # Get the broadcaster's user ID
    user = await first(twitch.get_users(logins=[login_name]))
    broadcaster_id = user.id

    # Retrieve the list of followers
    followers = await twitch.get_channel_followers(broadcaster_id=broadcaster_id)

    # Process the followers data
    for follower in followers.data:
        print(f"User ID: {follower.user_id}, User Name: {follower.user_name}, Followed At: {follower.followed_at}")

# Run the main function
asyncio.run(main())
