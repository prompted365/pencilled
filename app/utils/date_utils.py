from datetime import datetime, timedelta, time, date
from typing import List, Tuple, Optional

from app.config import settings


def get_date_range(start_date: Optional[date] = None, days: int = 7) -> Tuple[date, date]:
    """
    Get a date range starting from tomorrow (or specified date) for the given number of days.
    
    Args:
        start_date: The start date (defaults to tomorrow)
        days: Number of days to include (default: 7)
        
    Returns:
        Tuple of (start_date, end_date)
    """
    if start_date is None:
        # Start from tomorrow
        start_date = (datetime.now() + timedelta(days=1)).date()
    
    end_date = start_date + timedelta(days=days)
    return start_date, end_date


def get_business_hours_for_date(target_date: date) -> Tuple[datetime, datetime]:
    """
    Get the business hours start and end datetimes for a specific date.
    
    Args:
        target_date: The date to get business hours for
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    start_time = settings.get_business_hours_start_time()
    end_time = settings.get_business_hours_end_time()
    
    start_datetime = datetime.combine(target_date, start_time)
    end_datetime = datetime.combine(target_date, end_time)
    
    return start_datetime, end_datetime


def get_business_days_datetimes(
    start_date: Optional[date] = None, 
    days: int = 7
) -> List[Tuple[datetime, datetime]]:
    """
    Get a list of business hours start and end datetimes for a range of days.
    
    Args:
        start_date: The start date (defaults to tomorrow)
        days: Number of days to include (default: 7)
        
    Returns:
        List of tuples (start_datetime, end_datetime) for each day
    """
    start_date, end_date = get_date_range(start_date, days)
    
    result = []
    current_date = start_date
    
    while current_date < end_date:
        start_datetime, end_datetime = get_business_hours_for_date(current_date)
        result.append((start_datetime, end_datetime))
        current_date += timedelta(days=1)
    
    return result


def is_within_business_hours(dt: datetime) -> bool:
    """
    Check if a datetime is within business hours.
    
    Args:
        dt: The datetime to check
        
    Returns:
        True if within business hours, False otherwise
    """
    start_time = settings.get_business_hours_start_time()
    end_time = settings.get_business_hours_end_time()
    
    dt_time = dt.time()
    return start_time <= dt_time < end_time


def round_datetime_to_nearest(dt: datetime, minutes: int = 15) -> datetime:
    """
    Round a datetime to the nearest specified minutes.
    
    Args:
        dt: The datetime to round
        minutes: The minute interval to round to (default: 15)
        
    Returns:
        Rounded datetime
    """
    minutes_since_midnight = dt.hour * 60 + dt.minute
    rounded_minutes = round(minutes_since_midnight / minutes) * minutes
    
    rounded_hour = rounded_minutes // 60
    rounded_minute = rounded_minutes % 60
    
    return dt.replace(hour=rounded_hour, minute=rounded_minute, second=0, microsecond=0)


def format_time_for_display(dt: datetime) -> str:
    """
    Format a datetime for display to users.
    
    Args:
        dt: The datetime to format
        
    Returns:
        Formatted time string (e.g., "10:00 AM")
    """
    return dt.strftime("%-I:%M %p")  # %-I removes leading zero for 12-hour format


def format_datetime_for_display(dt: datetime) -> str:
    """
    Format a datetime for display to users, including date and time.
    
    Args:
        dt: The datetime to format
        
    Returns:
        Formatted datetime string (e.g., "Mon, Mar 16 at 10:00 AM")
    """
    return dt.strftime("%a, %b %-d at %-I:%M %p")
