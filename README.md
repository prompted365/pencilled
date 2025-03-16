# Pencilled

An appointment scheduling optimization system that integrates GoHighLevel API v2 with Google Routes Optimization API to suggest efficient appointment times based on technician availability and travel constraints.

## Features

- Fetches existing appointments from GoHighLevel API v2
- Identifies available time windows for new appointments
- Uses Google Routes Optimization API to calculate travel times
- Optimizes appointment slots based on technician location and travel constraints
- Provides optimal time slots for AI assistants to suggest to leads

## Setup

### Prerequisites

- Python 3.8+
- GoHighLevel API v2 private integration token
- Google Routes Optimization API key
- Google OAuth 2.0 client credentials (client_secret.json file)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/roncreteCrouter.git
   cd roncreteCrouter
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Copy the example environment file and update with your API keys:

   ```
   cp .env.example .env
   ```

   Edit the `.env` file to add your GoHighLevel token and Google API key.

## Configuration

The system is configurable through environment variables:

- `GHL_API_TOKEN`: Your GoHighLevel API v2 private integration token
- `GOOGLE_API_KEY`: Your Google Routes Optimization API key
- `GOOGLE_CLIENT_SECRET_FILE`: Path to the Google OAuth 2.0 client secret JSON file
- `BUSINESS_HOURS_START`: Start of business hours (default: "09:00")
- `BUSINESS_HOURS_END`: End of business hours (default: "18:00")
- `APPOINTMENT_BUFFER_MINUTES`: Buffer time between appointments in minutes (default: 15)
- `HOME_BASE_LAT`: Latitude of the home base/office location
- `HOME_BASE_LNG`: Longitude of the home base/office location
- `DEFAULT_APPOINTMENT_DURATION`: Default appointment duration in minutes (default: 60)
- `MAX_DAYS_AHEAD`: Maximum days ahead to schedule (default: 7)

## Usage

### Running Locally

```
uvicorn app.main:app --reload
```

The API will be available at <http://localhost:8000>

### API Endpoints

- `GET /api/slots`: Get optimized appointment slots
  - Query parameters:
    - `lead_address`: Address of the lead (required)
    - `appointment_duration`: Duration of the appointment in minutes (optional)
    - `date`: Specific date to check for slots (optional)

- `POST /api/appointments`: Create a new appointment
  - Request body:
    - `lead_id`: ID of the lead
    - `start_time`: Start time of the appointment (ISO 8601 format)
    - `address`: Address of the appointment
    - `duration`: Duration in minutes

## Deployment

### Deploying to Heroku

We've provided a deployment script to simplify the Heroku deployment process:

1. Make sure you have the Heroku CLI installed:
   ```
   brew install heroku/brew/heroku  # macOS
   # or follow instructions at https://devcenter.heroku.com/articles/heroku-cli
   ```

2. Run the deployment script:
   ```
   ./deploy_to_heroku.sh
   ```
   
   This script will:
   - Create a new Heroku app or use an existing one
   - Set all required environment variables from your .env file
   - Deploy the application to Heroku
   - Guide you through uploading the Google client secret file

3. Alternatively, you can deploy manually:
   ```
   # Create a Heroku app
   heroku create your-app-name
   
   # Set environment variables
   heroku config:set GHL_API_TOKEN=your_token
   heroku config:set GOOGLE_API_KEY=your_key
   heroku config:set ALLOWED_ORIGINS=https://yourdomain.com
   # Set other configuration variables as needed
   
   # Deploy the application
   git push heroku main
   ```

### Production Configuration

For production deployment, we recommend:

1. Create a `.env.prod` file with production-specific settings (already provided)
2. Set appropriate CORS origins for your production domain
3. Ensure all API keys and credentials are set as environment variables
4. Set LOG_LEVEL to "INFO" or "WARNING" for production

## Development

### Running Tests

```
pytest
```

### Google Routes Optimization API Authentication

This application uses the Google Routes Optimization API, which requires OAuth 2.0 authentication:

1. Create a project in the Google Cloud Console
2. Enable the Routes Optimization API
3. Create OAuth 2.0 credentials (client ID and client secret)
4. Download the client secret JSON file and place it in the project directory
5. Set the `GOOGLE_CLIENT_SECRET_FILE` environment variable to the path of this file
6. On first run, the application will open a browser window for you to authenticate
7. After authentication, a `token.json` file will be created to cache the credentials

### Code Structure

- `app/`: Main application package
  - `api/`: API endpoints
  - `services/`: Business logic and external API integrations
  - `models/`: Data models
  - `utils/`: Utility functions
- `tests/`: Test cases

## License

MIT
