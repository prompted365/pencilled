#!/bin/bash

# Script to deploy the RoncreteCrouter application to Heroku

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "Heroku CLI is not installed. Please install it first."
    echo "Visit: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if user is logged in to Heroku
heroku whoami &> /dev/null
if [ $? -ne 0 ]; then
    echo "You are not logged in to Heroku. Please login first."
    heroku login
fi

# Ask for app name
read -p "Enter your Heroku app name (or leave blank to create a new app): " APP_NAME

if [ -z "$APP_NAME" ]; then
    echo "Creating a new Heroku app..."
    APP_NAME=$(heroku create | grep -o 'https://[^ ]*' | sed 's/https:\/\///')
    echo "Created app: $APP_NAME"
else
    # Check if app exists
    heroku apps:info --app $APP_NAME &> /dev/null
    if [ $? -ne 0 ]; then
        echo "App $APP_NAME does not exist. Creating it..."
        heroku create $APP_NAME
    fi
fi

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    source .env
else
    echo "No .env file found. Please create one with your API keys and settings."
    exit 1
fi

# Set environment variables on Heroku
echo "Setting environment variables on Heroku..."
heroku config:set GHL_API_TOKEN="$GHL_API_TOKEN" --app $APP_NAME
heroku config:set GOOGLE_API_KEY="$GOOGLE_API_KEY" --app $APP_NAME
heroku config:set HOME_BASE_LAT="$HOME_BASE_LAT" --app $APP_NAME
heroku config:set HOME_BASE_LNG="$HOME_BASE_LNG" --app $APP_NAME
heroku config:set GHL_CALENDAR_ID="$GHL_CALENDAR_ID" --app $APP_NAME
heroku config:set GHL_LOCATION_ID="$GHL_LOCATION_ID" --app $APP_NAME
heroku config:set BUSINESS_HOURS_START="$BUSINESS_HOURS_START" --app $APP_NAME
heroku config:set BUSINESS_HOURS_END="$BUSINESS_HOURS_END" --app $APP_NAME
heroku config:set APPOINTMENT_BUFFER_MINUTES="$APPOINTMENT_BUFFER_MINUTES" --app $APP_NAME
heroku config:set DEFAULT_APPOINTMENT_DURATION="$DEFAULT_APPOINTMENT_DURATION" --app $APP_NAME
heroku config:set MAX_DAYS_AHEAD="$MAX_DAYS_AHEAD" --app $APP_NAME
heroku config:set LOG_LEVEL="INFO" --app $APP_NAME
heroku config:set CACHE_TTL="3600" --app $APP_NAME

# Ask for allowed origins
read -p "Enter allowed origins for CORS (comma-separated, e.g., https://yourdomain.com): " ALLOWED_ORIGINS
if [ -z "$ALLOWED_ORIGINS" ]; then
    ALLOWED_ORIGINS="https://yourdomain.com"
fi
heroku config:set ALLOWED_ORIGINS="$ALLOWED_ORIGINS" --app $APP_NAME

# Upload Google client secret file
if [ -f "$GOOGLE_CLIENT_SECRET_FILE" ]; then
    echo "Uploading Google client secret file..."
    # Create a temporary directory
    mkdir -p tmp
    cp "$GOOGLE_CLIENT_SECRET_FILE" tmp/client_secret.json
    
    # Set the environment variable to the new filename
    heroku config:set GOOGLE_CLIENT_SECRET_FILE="client_secret.json" --app $APP_NAME
    
    echo "You will need to manually upload the client_secret.json file to your Heroku app."
    echo "You can do this by running:"
    echo "heroku run 'mkdir -p ./' --app $APP_NAME"
    echo "cat tmp/client_secret.json | heroku run 'cat > client_secret.json' --app $APP_NAME"
else
    echo "Google client secret file not found. Make sure to upload it manually to Heroku."
fi

# Deploy to Heroku
echo "Deploying to Heroku..."
git push heroku main

# Clean up
rm -rf tmp

echo "Deployment complete! Your app is running at: https://$APP_NAME.herokuapp.com"
echo "You can check the logs with: heroku logs --tail --app $APP_NAME"
