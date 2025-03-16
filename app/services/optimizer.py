from datetime import datetime, timedelta, date
from typing import List, Optional, Tuple, Dict

from loguru import logger

from app.config import settings
from app.models.appointment import Appointment, Location
from app.models.time_window import TimeWindow
from app.models.candidate_slot import CandidateSlot, AvailableSlot
from app.services.gohighlevel import GoHighLevelService
from app.services.google_routes import GoogleRoutesService
from app.utils.date_utils import (
    get_business_days_datetimes,
    is_within_business_hours,
    round_datetime_to_nearest
)


class AppointmentOptimizer:
    """Service for optimizing appointment slots based on travel time and availability."""
    
    def __init__(self):
        self.ghl_service = GoHighLevelService()
        self.routes_service = GoogleRoutesService()
        self.buffer_minutes = settings.APPOINTMENT_BUFFER_MINUTES
        self.home_base = Location(
            lat=settings.HOME_BASE_LAT,
            lng=settings.HOME_BASE_LNG,
            address="Home Base"
        )
    
    def get_free_time_windows(
        self, 
        appointments: List[Appointment],
        start_date: Optional[date] = None,
        days: int = 7
    ) -> List[TimeWindow]:
        """
        Identify free time windows between appointments.
        
        Args:
            appointments: List of existing appointments
            start_date: Start date for the time windows (default: tomorrow)
            days: Number of days to consider (default: 7)
            
        Returns:
            List of TimeWindow objects representing free time slots
        """
        # Get business hours for each day
        business_hours = get_business_days_datetimes(start_date, days)
        
        # Sort appointments by start time
        sorted_appointments = sorted(appointments, key=lambda a: a.start_time)
        
        free_windows = []
        
        # Process each business day
        for day_start, day_end in business_hours:
            day_appointments = [
                a for a in sorted_appointments 
                if day_start.date() == a.start_time.date()
            ]
            
            # If no appointments for this day, add the entire day as a free window
            if not day_appointments:
                free_windows.append(
                    TimeWindow(
                        start_time=day_start,
                        end_time=day_end,
                        start_location=self.home_base,
                        end_location=self.home_base
                    )
                )
                continue
            
            # Add window before first appointment if needed
            first_appt = day_appointments[0]
            if day_start < first_appt.start_time:
                # Determine start location (home base)
                free_windows.append(
                    TimeWindow(
                        start_time=day_start,
                        end_time=first_appt.start_time,
                        start_location=self.home_base,
                        end_location=first_appt.location
                    )
                )
            
            # Add windows between appointments
            for i in range(len(day_appointments) - 1):
                current_appt = day_appointments[i]
                next_appt = day_appointments[i + 1]
                
                if current_appt.end_time < next_appt.start_time:
                    free_windows.append(
                        TimeWindow(
                            start_time=current_appt.end_time,
                            end_time=next_appt.start_time,
                            start_location=current_appt.location,
                            end_location=next_appt.location
                        )
                    )
            
            # Add window after last appointment if needed
            last_appt = day_appointments[-1]
            if last_appt.end_time < day_end:
                # Determine end location (home base)
                free_windows.append(
                    TimeWindow(
                        start_time=last_appt.end_time,
                        end_time=day_end,
                        start_location=last_appt.location,
                        end_location=self.home_base
                    )
                )
        
        return free_windows
    
    def generate_candidate_slots(
        self,
        free_windows: List[TimeWindow],
        lead_location: Location,
        appointment_duration: int = 60,
        interval_minutes: int = 15
    ) -> List[CandidateSlot]:
        """
        Generate candidate appointment slots from free time windows.
        
        Args:
            free_windows: List of free time windows
            lead_location: Location of the lead/appointment
            appointment_duration: Duration of the appointment in minutes
            interval_minutes: Interval for slot start times in minutes
            
        Returns:
            List of CandidateSlot objects
        """
        candidate_slots = []
        
        for window in free_windows:
            # Skip windows that are too short for the appointment plus buffer
            required_minutes = appointment_duration + (self.buffer_minutes * 2)
            if window.duration_minutes < required_minutes:
                continue
            
            # Calculate travel times
            travel_time_to = self.routes_service.get_travel_time(
                window.start_location, lead_location
            )
            travel_time_from = self.routes_service.get_travel_time(
                lead_location, window.end_location
            )
            
            # Calculate earliest possible start time (after travel from previous location)
            earliest_start = window.start_time + timedelta(minutes=travel_time_to + self.buffer_minutes)
            earliest_start = round_datetime_to_nearest(earliest_start, interval_minutes)
            
            # Calculate latest possible end time (allowing travel to next location)
            latest_end = window.end_time - timedelta(minutes=travel_time_from + self.buffer_minutes)
            
            # Calculate latest possible start time
            latest_start = latest_end - timedelta(minutes=appointment_duration)
            latest_start = round_datetime_to_nearest(latest_start, interval_minutes)
            
            # Skip if earliest start is after latest start
            if earliest_start > latest_start:
                continue
            
            # Generate candidate slots at specified intervals
            current_start = earliest_start
            while current_start <= latest_start:
                current_end = current_start + timedelta(minutes=appointment_duration)
                
                # Skip slots that extend beyond the window
                if current_end > window.end_time - timedelta(minutes=travel_time_from + self.buffer_minutes):
                    break
                
                # Calculate efficiency score (lower is better)
                # Base score on total travel time
                total_travel_time = travel_time_to + travel_time_from
                
                # Adjust score based on time of day (prefer mid-day)
                hour = current_start.hour
                time_of_day_factor = 1.0
                if 10 <= hour <= 14:  # Prefer mid-day (10 AM - 2 PM)
                    time_of_day_factor = 0.9
                elif hour < 9 or hour > 16:  # Less preferred early morning or late afternoon
                    time_of_day_factor = 1.1
                
                # Calculate final score (lower is better)
                efficiency_score = total_travel_time * time_of_day_factor
                
                # Create candidate slot
                slot = CandidateSlot(
                    start_time=current_start,
                    end_time=current_end,
                    lead_location=lead_location,
                    travel_time_to_minutes=travel_time_to,
                    travel_time_from_minutes=travel_time_from,
                    efficiency_score=efficiency_score,
                    previous_location=window.start_location,
                    next_location=window.end_location
                )
                
                candidate_slots.append(slot)
                
                # Move to next interval
                current_start += timedelta(minutes=interval_minutes)
        
        return candidate_slots
    
    def get_optimized_slots(
        self,
        lead_address: str,
        appointment_duration: int = 60,
        target_date: Optional[date] = None,
        max_slots: int = 10
    ) -> List[AvailableSlot]:
        """
        Get optimized appointment slots for a lead.
        
        Args:
            lead_address: Address of the lead
            appointment_duration: Duration of the appointment in minutes
            target_date: Specific date to check for slots (optional)
            max_slots: Maximum number of slots to return
            
        Returns:
            List of AvailableSlot objects sorted by efficiency score
        """
        # Geocode the lead address
        lead_location = self.routes_service.geocode_address(lead_address)
        if not lead_location:
            logger.error(f"Could not geocode lead address: {lead_address}")
            return []
        
        # Set date range
        start_date = target_date if target_date else None
        days = 1 if target_date else settings.MAX_DAYS_AHEAD
        
        # Get existing appointments
        appointments = self.ghl_service.get_appointments()
        
        # Get free time windows
        free_windows = self.get_free_time_windows(appointments, start_date, days)
        
        # Generate candidate slots
        candidate_slots = self.generate_candidate_slots(
            free_windows, lead_location, appointment_duration
        )
        
        # Sort candidate slots by efficiency score (lower is better)
        sorted_slots = sorted(candidate_slots, key=lambda s: s.efficiency_score)
        
        # Convert to API response format
        available_slots = []
        for slot in sorted_slots[:max_slots]:
            # Normalize efficiency score to 0-100 range (higher is better)
            # Assuming efficiency scores typically range from 0 to 200 (minutes of travel time)
            normalized_score = max(0, min(100, 100 - (slot.efficiency_score / 2)))
            
            available_slots.append(
                AvailableSlot(
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    efficiency_score=normalized_score
                )
            )
        
        return available_slots
