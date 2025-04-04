# NeRF Gun Control System

A Twitch-integrated Nerf gun control system that allows Twitch viewers to control a physical Nerf gun through chat commands.

## System Overview

This project consists of several components:

1. **Twitch Bot**: Listens to Twitch chat commands and controls the Nerf gun
2. **Admin Interface**: Streamlit-based web interface for managing the system
3. **Database**: Stores subscriber information, subscription levels, and system configuration
4. **Nerf Controller**: Interfaces with the physical Nerf gun hardware

## Prerequisites

- Python 3.11 or higher
- Poetry (Python package manager)
- MySQL database
- Twitch Developer Account (for API access)
- Physical Nerf gun setup with controller

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd nerf-gun-control
```

### 2. Install dependencies

```bash
poetry install
```

### 3. Set up environment variables

Create a `.env` file in the project root with the following variables:

```
# Twitch API Credentials
TWITCH_CLIENT_ID=your_client_id
TWITCH_SECRET=your_client_secret
TWITCH_ACCESS_TOKEN=your_access_token
TWITCH_REFRESH_TOKEN=your_refresh_token
TWITCH_CHANNEL_NAME=your_channel_name

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=nerfbot_db

# Nerf Controller Configuration
NERF_CONTROLLER_URL=http://localhost:5555
```

### 4. Set up the database

Run the database setup script:

```bash
mysql -u your_db_user -p < nerf-admin/nerfdb-setup.sql
```

## Running the System

### Starting the Nerf Gun Control System

On Windows, you can use the provided batch file:

```bash
./start_nerf.bat
```

Or start the components individually:

1. Start the admin interface:

```bash
poetry run streamlit run nerf-admin/nerf-admin.py
```

2. Start the Twitch bot:

```bash
poetry run start
# or
poetry run python nerf-gun-control/main.py
```

### Twitch Commands

Users can control the Nerf gun with the following commands in Twitch chat:

- `!fire x y z` - Fire the Nerf gun at coordinates (x, y) with z shots
- `!credits` - Check remaining credits
- `!help` - Display available commands

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting and Linting

```bash
# Format code
poetry run black .

# Lint code
poetry run flake8
```

### Simulator Mode

For development without physical hardware, you can use the Nerf gun simulator:

```bash
python nerf-gun-simulator/simulator.py
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure your Twitch tokens are valid and have the correct scopes
2. **Database Connection Issues**: Verify database credentials and that the MySQL server is running
3. **Nerf Controller Not Responding**: Check that the controller is powered on and the URL is correct

## License

[Specify your license here]

## Contributing

Contributions are welcome! See [MOREWORK.md](MOREWORK.md) for enhancement ideas and future development plans.
