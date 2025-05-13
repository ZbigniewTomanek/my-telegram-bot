# Personal Health & Fitness Telegram Bot

A Telegram bot that helps you track your health data, including food and medication logs, as well as Garmin Connect health metrics.

## Documentation

- [Garmin Data Reference](docs/garmin_data_reference.md) - Comprehensive documentation of all data exported from Garmin Connect

## Features

### Core Features
- 🍽️ **Food Logging** - Log your meals with nutritional information (protein, carbs, fats)
- 💊 **Medication Tracking** - Keep track of medications and dosages
- 📋 **Data Listing** - View your recent food and medication entries

### Garmin Connect Integration
- 🔄 **Garmin Connect Sync** - Link your Garmin Connect account
- 📊 **Health Reports** - Export health and fitness data in multiple formats
- 📅 **Date Range Selection** - View data for custom time periods
- 🔒 **Secure Authentication** - MFA support and secure token storage

## Installation

### Prerequisites
- Python 3.12+
- Poetry (dependency management)
- A Telegram Bot API key (from BotFather)
- A Garmin Connect account (for health metrics)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd telegram-bot
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Create an environment file**
   Create a `.env` file in the root directory with:
   ```
   TELEGRAM_BOT_API_KEY=your_telegram_bot_api_key
   MY_TELEGRAM_USER_ID=your_telegram_user_id
   READ_TIMEOUT_S=30
   WRITE_TIMEOUT_S=30
   ```

## Usage

### Running the Bot

Start the bot using Poetry:
```bash
poetry run python -m telegram_bot.main
```

Or directly with Python:
```bash
python -m telegram_bot.main
```

### Available Commands

#### Core Commands
- `/log_food` - Start conversation to log food
- `/log_drug` - Start conversation to log medication
- `/list_food` - List recent food logs
- `/list_drugs` - List recent medication logs

#### Garmin Connect Commands
- `/connect_garmin` - Link your Garmin Connect account
- `/garmin_status` - Check connection status
- `/garmin_export` - Export health and fitness data
- `/disconnect_garmin` - Unlink your Garmin account

## Systemd Service

To run the bot as a systemd service, use the included script:
```bash
sudo ./run-as-systemd-service.sh
```

This will install and enable a systemd service that runs the bot on startup.

## Data Storage

- SQLite database for food and medication logs
- Secure token storage for Garmin Connect authentication
- All data is stored locally in the `out` directory

## Privacy & Security

- The bot is designed for personal use and only responds to a single authorized user
- Garmin Connect credentials are used only for authentication and not stored
- MFA support for secure authentication
- Token-based authentication to minimize credential usage

## Development

### Project Structure
- `telegram_bot/` - Main package
  - `handlers/` - Bot command and conversation handlers
  - `service/` - Business logic services
  - `main.py` - Application entry point

### Adding New Features
1. Add service logic in `telegram_bot/service/`
2. Create handlers in `telegram_bot/handlers/`
3. Register handlers in `telegram_bot/main.py`

## License

[MIT License](LICENSE)