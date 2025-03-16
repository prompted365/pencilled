from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.appointment import Location


class TimeWindow(BaseModel):
    """Model representing a time window between appointments."""
    start_time: datetime
    end_time: datetime
    start_location: Location
    end_location: Location
    
    @field_validator("end_time")
    def end_time_after_start_time(cls, v, info):
        """Validate that end_time is after start_time."""
        data = info.data
        if "start_time" in data and v <= data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v
    
    @property
    def duration_minutes(self) -> int:
        """Calculate the duration of the time window in minutes."""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)
    
    def is_valid_for_duration(self, duration_minutes: int, buffer_minutes: int = 0) -> bool:
        """Check if the time window can accommodate an appointment of the given duration."""
        required_minutes = duration_minutes + (buffer_minutes * 2)  # Buffer before and after
        return self.duration_minutes >= required_minutes
    
    def contains_time(self, dt: datetime) -> bool:
        """Check if the given datetime is within this time window."""
        return self.start_time <= dt < self.end_time
    
    def overlaps_with(self, other: 'TimeWindow') -> bool:
        """Check if this time window overlaps with another time window."""
        return (
            (self.start_time <= other.start_time < self.end_time) or
            (self.start_time < other.end_time <= self.end_time) or
            (other.start_time <= self.start_time and other.end_time >= self.end_time)
        )
    
    def __str__(self) -> str:
        """String representation of the time window."""
        return f"TimeWindow({self.start_time.isoformat()} to {self.end_time.isoformat()}, {self.duration_minutes} minutes)"
