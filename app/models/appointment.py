from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    """Location model with latitude and longitude."""
    lat: float
    lng: float
    address: Optional[str] = None


class Appointment(BaseModel):
    """Model representing an appointment from GoHighLevel."""
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    location: Location
    contact_id: Optional[str] = None
    calendar_id: str
    location_id: str
    raw_data: Optional[Dict[str, Any]] = None

    @field_validator("duration_minutes", mode="before")
    def calculate_duration(cls, v, info):
        """Calculate duration in minutes if not provided."""
        if v is not None:
            return v
        
        data = info.data
        if "start_time" in data and "end_time" in data:
            delta = data["end_time"] - data["start_time"]
            return int(delta.total_seconds() / 60)
        
        return 60  # Default duration if times not available

    class Config:
        schema_extra = {
            "example": {
                "id": "abc123",
                "title": "Concrete Coating Consultation",
                "start_time": "2025-03-16T10:00:00Z",
                "end_time": "2025-03-16T11:00:00Z",
                "duration_minutes": 60,
                "location": {
                    "lat": 40.7128,
                    "lng": -74.0060,
                    "address": "123 Main St, New York, NY 10001"
                },
                "contact_id": "contact123",
                "calendar_id": "cal123",
                "location_id": "loc123"
            }
        }


class AppointmentCreate(BaseModel):
    """Model for creating a new appointment."""
    lead_id: str
    start_time: datetime
    address: str
    duration_minutes: int = Field(default=60, ge=15)
    title: Optional[str] = "Concrete Coating Consultation"

    class Config:
        schema_extra = {
            "example": {
                "lead_id": "contact123",
                "start_time": "2025-03-16T10:00:00Z",
                "address": "123 Main St, New York, NY 10001",
                "duration_minutes": 60,
                "title": "Concrete Coating Consultation"
            }
        }


class AppointmentResponse(BaseModel):
    """Response model for appointment creation."""
    id: str
    start_time: datetime
    end_time: datetime
    title: str
    success: bool = True
    message: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "id": "abc123",
                "start_time": "2025-03-16T10:00:00Z",
                "end_time": "2025-03-16T11:00:00Z",
                "title": "Concrete Coating Consultation",
                "success": True,
                "message": "Appointment created successfully"
            }
        }
