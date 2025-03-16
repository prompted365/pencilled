from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import requests
from loguru import logger

from app.config import settings
from app.models.appointment import Appointment, Location, AppointmentCreate, AppointmentResponse
from app.utils.distance_utils import geocode_address as utils_geocode_address


class GoHighLevelAPIError(Exception):
    """Exception raised for GoHighLevel API errors."""
    pass


class GoHighLevelService:
    """Service for interacting with the GoHighLevel API v2."""
    
    def __init__(self):
        self.base_url = settings.GHL_API_BASE_URL
        self.token = settings.GHL_API_TOKEN
        self.calendar_id = settings.GHL_CALENDAR_ID
        self.location_id = settings.GHL_LOCATION_ID
        self.api_version = settings.GHL_API_VERSION
        
        if not self.token:
            logger.warning("GoHighLevel API token not set")
        
        if not self.calendar_id:
            logger.warning("GoHighLevel calendar ID not set")
        
        if not self.location_id:
            logger.warning("GoHighLevel location ID not set")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get the headers for API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": self.api_version
        }
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle the API response and raise exceptions for errors."""
        if response.status_code >= 400:
            error_message = f"GoHighLevel API error: {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_message = f"{error_message} - {error_data['message']}"
            except Exception:
                error_message = f"{error_message} - {response.text}"
            
            logger.error(error_message)
            raise GoHighLevelAPIError(error_message)
        
        return response.json()
    
    def geocode_address(self, address: str) -> Optional[Location]:
        """
        Geocode an address to get latitude and longitude.
        This method delegates to the utility function in distance_utils.
        
        Args:
            address: The address to geocode
            
        Returns:
            Location object with lat and lng, or None if geocoding failed
        """
        return utils_geocode_address(address)
    
    def get_appointments(
        self, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> List[Appointment]:
        """
        Get appointments from the GoHighLevel calendar.
        
        Args:
            start_time: Start time for filtering appointments (default: tomorrow)
            end_time: End time for filtering appointments (default: 7 days from start_time)
            
        Returns:
            List of Appointment objects
        """
        if not self.token or not self.calendar_id or not self.location_id:
            logger.error("Missing required GoHighLevel credentials")
            return []
        
        # Set default time range if not provided
        if start_time is None:
            start_time = datetime.now() + timedelta(days=1)
            start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_time is None:
            end_time = start_time + timedelta(days=settings.MAX_DAYS_AHEAD)
        
        # Format times for API
        start_time_str = start_time.isoformat()
        end_time_str = end_time.isoformat()
        
        # Build URL
        url = f"{self.base_url}/calendars/events"
        
        # Set query parameters
        params = {
            "calendarId": self.calendar_id,
            "locationId": self.location_id,
            "startTime": start_time_str,
            "endTime": end_time_str
        }
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            data = self._handle_response(response)
            
            appointments = []
            for event in data.get("events", []):
                # Skip events that are not appointments
                if event.get("type") != "appointment":
                    continue
                
                # Extract location data
                location_data = event.get("location", {})
                location = Location(
                    lat=location_data.get("latitude", 0.0),
                    lng=location_data.get("longitude", 0.0),
                    address=location_data.get("address", "")
                )
                
                # Create appointment object
                appointment = Appointment(
                    id=event.get("id", ""),
                    title=event.get("title", "Appointment"),
                    start_time=datetime.fromisoformat(event.get("startTime").replace("Z", "+00:00")),
                    end_time=datetime.fromisoformat(event.get("endTime").replace("Z", "+00:00")),
                    duration_minutes=event.get("durationInMinutes", 60),
                    location=location,
                    contact_id=event.get("contactId"),
                    calendar_id=event.get("calendarId", self.calendar_id),
                    location_id=event.get("locationId", self.location_id),
                    raw_data=event
                )
                
                appointments.append(appointment)
            
            return appointments
        except Exception as e:
            logger.exception(f"Error fetching appointments: {e}")
            return []
    
    def create_appointment(self, appointment_data: AppointmentCreate) -> AppointmentResponse:
        """
        Create a new appointment in GoHighLevel.
        
        Args:
            appointment_data: AppointmentCreate object with appointment details
            
        Returns:
            AppointmentResponse object
        """
        if not self.token or not self.calendar_id or not self.location_id:
            error_msg = "Missing required GoHighLevel credentials"
            logger.error(error_msg)
            return AppointmentResponse(
                id="",
                start_time=appointment_data.start_time,
                end_time=appointment_data.start_time + timedelta(minutes=appointment_data.duration_minutes),
                title=appointment_data.title,
                success=False,
                message=error_msg
            )
        
        # Calculate end time
        end_time = appointment_data.start_time + timedelta(minutes=appointment_data.duration_minutes)
        
        # Geocode the address if needed
        location = self.geocode_address(appointment_data.address)
        
        if not location:
            error_msg = f"Could not geocode address: {appointment_data.address}"
            logger.error(error_msg)
            return AppointmentResponse(
                id="",
                start_time=appointment_data.start_time,
                end_time=end_time,
                title=appointment_data.title,
                success=False,
                message=error_msg
            )
        
        # Build URL
        url = f"{self.base_url}/calendars/events/appointments"
        
        # Prepare payload
        payload = {
            "calendarId": self.calendar_id,
            "locationId": self.location_id,
            "contactId": appointment_data.lead_id,
            "title": appointment_data.title,
            "startTime": appointment_data.start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "durationInMinutes": appointment_data.duration_minutes,
            "location": {
                "address": appointment_data.address,
                "latitude": location.lat,
                "longitude": location.lng
            }
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            data = self._handle_response(response)
            
            return AppointmentResponse(
                id=data.get("id", ""),
                start_time=appointment_data.start_time,
                end_time=end_time,
                title=appointment_data.title,
                success=True,
                message="Appointment created successfully"
            )
        except GoHighLevelAPIError as e:
            logger.exception(f"Error creating appointment: {e}")
            return AppointmentResponse(
                id="",
                start_time=appointment_data.start_time,
                end_time=end_time,
                title=appointment_data.title,
                success=False,
                message=str(e)
            )
        except Exception as e:
            logger.exception(f"Unexpected error creating appointment: {e}")
            return AppointmentResponse(
                id="",
                start_time=appointment_data.start_time,
                end_time=end_time,
                title=appointment_data.title,
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
