import os
from datetime import time
from typing import Optional

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    # API Keys
    GHL_API_TOKEN: str
    GOOGLE_API_KEY: str
    GOOGLE_CLIENT_SECRET_FILE: str = "client_secret.json"

    # Business Hours (24-hour format)
    BUSINESS_HOURS_START: str = "09:00"
    BUSINESS_HOURS_END: str = "18:00"

    # Appointment Settings
    APPOINTMENT_BUFFER_MINUTES: int = 15
    DEFAULT_APPOINTMENT_DURATION: int = 60
    MAX_DAYS_AHEAD: int = 7

    # Home Base Location (office/starting point)
    HOME_BASE_LAT: float
    HOME_BASE_LNG: float

    # GoHighLevel Settings
    GHL_CALENDAR_ID: str
    GHL_LOCATION_ID: str
    GHL_API_VERSION: str = "2021-07-28"
    GHL_API_BASE_URL: str = "https://services.leadconnectorhq.com"

    # Google Routes API Settings
    GOOGLE_ROUTES_API_BASE_URL: str = "https://routes.googleapis.com/v2/optimizeRoutes"

    # Application Settings
    LOG_LEVEL: str = "INFO"
    CACHE_TTL: int = 3600  # Time-to-live for cached travel times in seconds
    
    # CORS Settings
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @field_validator("BUSINESS_HOURS_START", "BUSINESS_HOURS_END")
    def validate_time_format(cls, v):
        try:
            hours, minutes = map(int, v.split(":"))
            if not (0 <= hours < 24 and 0 <= minutes < 60):
                raise ValueError("Invalid time format")
            return v
        except Exception:
            raise ValueError(f"Invalid time format: {v}. Use HH:MM format (24-hour).")

    def get_business_hours_start_time(self) -> time:
        """Convert BUSINESS_HOURS_START string to time object."""
        hours, minutes = map(int, self.BUSINESS_HOURS_START.split(":"))
        return time(hours, minutes)

    def get_business_hours_end_time(self) -> time:
        """Convert BUSINESS_HOURS_END string to time object."""
        hours, minutes = map(int, self.BUSINESS_HOURS_END.split(":"))
        return time(hours, minutes)

    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


# Create settings instance
settings = Settings(
    # Set default values for required fields if not in environment
    GHL_API_TOKEN=os.getenv("GHL_API_TOKEN", ""),
    GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY", ""),
    HOME_BASE_LAT=float(os.getenv("HOME_BASE_LAT", "0")),
    HOME_BASE_LNG=float(os.getenv("HOME_BASE_LNG", "0")),
    GHL_CALENDAR_ID=os.getenv("GHL_CALENDAR_ID", ""),
    GHL_LOCATION_ID=os.getenv("GHL_LOCATION_ID", ""),
    CACHE_TTL=int(os.getenv("CACHE_TTL", "3600").split("#")[0].strip()),
)
