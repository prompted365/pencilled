from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.appointment import Location


class CandidateSlot(BaseModel):
    """Model representing a candidate appointment slot."""
    start_time: datetime
    end_time: datetime
    lead_location: Location
    travel_time_to_minutes: int
    travel_time_from_minutes: int
    efficiency_score: float
    previous_location: Optional[Location] = None
    next_location: Optional[Location] = None
    
    @property
    def duration_minutes(self) -> int:
        """Calculate the duration of the appointment in minutes."""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)
    
    @property
    def total_travel_time_minutes(self) -> int:
        """Calculate the total travel time in minutes."""
        return self.travel_time_to_minutes + self.travel_time_from_minutes
    
    def __str__(self) -> str:
        """String representation of the candidate slot."""
        return (
            f"CandidateSlot({self.start_time.isoformat()}, "
            f"travel: {self.total_travel_time_minutes} min, "
            f"score: {self.efficiency_score:.2f})"
        )


class SlotRequest(BaseModel):
    """Model for requesting available appointment slots."""
    lead_address: str
    appointment_duration: Optional[int] = Field(default=60, ge=15)
    date: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "lead_address": "123 Main St, New York, NY 10001",
                "appointment_duration": 60,
                "date": "2025-03-16T00:00:00Z"
            }
        }


class AvailableSlot(BaseModel):
    """Model representing an available appointment slot for the API response."""
    start_time: datetime
    end_time: datetime
    efficiency_score: float
    
    class Config:
        schema_extra = {
            "example": {
                "start_time": "2025-03-16T10:00:00Z",
                "end_time": "2025-03-16T11:00:00Z",
                "efficiency_score": 95.5
            }
        }


class AvailableSlotsResponse(BaseModel):
    """Response model for available appointment slots."""
    slots: List[AvailableSlot]
    lead_address: str
    appointment_duration: int
    date: Optional[datetime] = None
    message: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "slots": [
                    {
                        "start_time": "2025-03-16T10:00:00Z",
                        "end_time": "2025-03-16T11:00:00Z",
                        "efficiency_score": 95.5
                    },
                    {
                        "start_time": "2025-03-16T14:00:00Z",
                        "end_time": "2025-03-16T15:00:00Z",
                        "efficiency_score": 87.2
                    }
                ],
                "lead_address": "123 Main St, New York, NY 10001",
                "appointment_duration": 60,
                "date": "2025-03-16T00:00:00Z",
                "message": "Found 2 available slots"
            }
        }
