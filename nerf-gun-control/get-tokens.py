import os
from re import T
import sys
from numpy import dot
import requests
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os


load_dotenv(".env", override=True)

# Replace these with your Twitch Client ID and Client Secret
CLIENT_ID = os.getenv("BOT_CLIENT_ID")
CLIENT_SECRET = os.getenv('BOT_CLIENT_SECRET')


# The port number should match the one specified in the redirect URI
REDIRECT_URI = 'http://localhost:8080'
AUTHORIZATION_BASE_URL = 'https://id.twitch.tv/oauth2/authorize'
TOKEN_URL = 'https://id.twitch.tv/oauth2/token'

# Scopes required for the bot
SCOPES = [
    'chat:read',
    'chat:edit',
    'whispers:read',
    'whispers:edit',
    'channel:read:subscriptions',
    'moderator:read:followers',
]

# Global variable to store the authorization code
authorization_code = ''

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global authorization_code
        # Parse the URL to get the code parameter
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        if 'code' in query_params:
            authorization_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>Authorization Successful</h1><p>You can close this window.</p>')
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'<h1>Authorization Failed</h1><p>No authorization code found.</p>')

def start_server(server_class=HTTPServer, handler_class=OAuthHandler):
    server_address = ('', 8080)  # Listen on port 8080
    httpd = server_class(server_address, handler_class)
    httpd.handle_request()  # Handle a single request
    httpd.server_close()

def main():
    global authorization_code

    # Step 1: Construct the authorization URL
    auth_url = (
        f"{AUTHORIZATION_BASE_URL}"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={' '.join(SCOPES)}"
    )

    # Step 2: Start the local server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

    # Step 3: Open the authorization URL in the default web browser
    print('Opening the authorization URL in your browser...')
    webbrowser.open(auth_url)

    # Wait for the server thread to finish (i.e., wait for the authorization code)
    server_thread.join()

    if not authorization_code:
        print('Failed to obtain authorization code.')
        sys.exit(1)

    # Step 4: Exchange the authorization code for an access token
    print('Exchanging authorization code for access token...')
    token_params = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': authorization_code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }

    response = requests.post(TOKEN_URL, data=token_params)
    if response.status_code != 200:
        print('Failed to obtain access token.')
        print(f'Status Code: {response.status_code}')
        print(f'Response: {response.text}')
        sys.exit(1)

    token_data = response.json()
    access_token = token_data['access_token']
    refresh_token = token_data.get('refresh_token', '')

    # Step 5: Print the access token and refresh token
    print('Access Token:', access_token)
    print('Refresh Token:', refresh_token)
    print('Token Type:', token_data['token_type'])
    print('Expires In:', token_data['expires_in'])
    print('Scopes:', ', '.join(token_data['scope']))

    # Save tokens to a file (optional)
    with open('tokens.txt', 'w') as token_file:
        token_file.write(f"Access Token: {access_token}\n")
        token_file.write(f"Refresh Token: {refresh_token}\n")
        token_file.write(f"Expires In: {token_data['expires_in']}\n")
        token_file.write(f"Scopes: {', '.join(token_data['scope'])}\n")

    print('Tokens saved to tokens.txt')

if __name__ == '__main__':
    main()