# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development and Testing
- **Install dependencies**: `poetry install`
- **Start the Twitch bot**: `poetry run start` or `poetry run python nerf-gun-control/main.py`
- **Start admin interface**: `poetry run streamlit run nerf-admin/nerf-admin.py`
- **Run all tests**: `poetry run pytest`
- **Run specific test**: `poetry run pytest nerf-gun-control/test_nerf_controller.py`
- **Code formatting**: `poetry run black .`
- **Code linting**: `poetry run flake8`
- **Start simulator**: `python nerf-gun-simulator/simulator.py`

### Database Management
- **Setup database**: `mysql -u your_db_user -p < nerf-admin/nerfdb-setup.sql`
- **Test database connection**: `python nerf-admin/test-db.py`

### System Control
- **Windows batch start**: `./start_nerf.bat`
- **PowerShell start**: `./new-start-nerf.ps1`

## Architecture Overview

This is a Twitch-integrated Nerf gun control system with several key components:

### Core Components

1. **Twitch Bot** (`nerf-gun-control/main.py`):
   - Main entry point with `NerfGunBot` class extending TwitchIO
   - Handles chat commands: `!fire x y z`, `!credits`, `!addbonus`
   - Manages user authentication, subscription checking, and credit systems
   - Implements watchdog system for automatic home position return
   - Uses async/await extensively for database and API operations

2. **Nerf Controller** (`nerf-gun-control/nerf_controller.py`):
   - `NerfController` class interfaces with physical gun hardware
   - REST API communication to gun server (default: localhost:5555)
   - Handles firing commands, status checking, and gun positioning

3. **Admin Interface** (`nerf-admin/nerf-admin.py`):
   - Streamlit-based web interface for system management
   - Database connection and configuration management
   - User credit management and system monitoring

4. **Database Layer**:
   - MySQL database with tables for subscribers, system_config, subscription_levels
   - Handles user credits, subscription levels, and gun configuration
   - Connection pooling using aiomysql

### Key Features

- **Credit System**: Users consume credits to fire shots, with different rates based on subscription level
- **Follower/Subscription Verification**: Checks Twitch follower status and subscription before allowing commands
- **Gun Safety**: Angle limits, home position, and automatic timeout/return to home
- **OBS Integration**: Logs messages to file for OBS text source display
- **Token Management**: Automatic Twitch token refresh handling

### Configuration

- Environment variables in `.env` file for Twitch API, database, and gun controller settings
- Database-stored configuration for gun angles, offsets, and system behavior
- Parameters defined in `nerf-gun-control/params.py`

### Testing

- Unit tests in `nerf-gun-control/test_nerf_controller.py`
- Integration tests in `nerf-gun-control/test/test_nerf_controller_integration.py`
- Database testing utilities in `nerf-admin/test-db.py`

### WordPress Integration (Legacy)

- WordPress API endpoints exist but appear deprecated in favor of direct MySQL
- Methods prefixed with `wp_` in main.py are legacy WordPress integration code

### Deployment Options

- Docker Compose setup available (`docker-compose.yml`)
- Poetry for Python dependency management
- Batch/PowerShell scripts for Windows deployment

## Development Notes

- Uses Python 3.11+ with Poetry for dependency management
- Code style: Black formatter with 100 character line length
- All async operations use proper lock management for thread safety
- Extensive error handling and logging throughout the system
- Gun controller implements wait patterns and status polling for reliability