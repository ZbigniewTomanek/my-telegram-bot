#!/bin/bash

# Configuration
BOT_NAME="my-telegram-bot"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_FILE="$HOME/Library/LaunchAgents/com.user.${BOT_NAME}.plist"
LOG_FILE="$PROJECT_DIR/out/log/service.log"

# Create the logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/out/log"

# Create the LaunchAgent plist file
cat >"$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.${BOT_NAME}</string>

    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>${PROJECT_DIR}</string>
    </dict>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>source "${PROJECT_DIR}/.env" && docker run --rm -v "${PROJECT_DIR}:/app" -w /app --env-file .env -e PYTHONPATH=/app --name telegram_bot ghcr.io/astral-sh/uv:python3.13-alpine uv run --isolated telegram_bot/main.py</string>
    </array>

    <key>StandardOutPath</key>
    <string>${LOG_FILE}</string>

    <key>StandardErrorPath</key>
    <string>${LOG_FILE}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

# Set proper permissions
chmod 644 "$PLIST_FILE"

# Load the service
launchctl load "$PLIST_FILE"

echo "Telegram bot service has been set up!"
echo "Service logs are available at: $LOG_FILE"
