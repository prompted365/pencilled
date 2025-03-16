import math
import os
import json
from typing import Tuple, Dict, Any, Optional, List
from functools import lru_cache

import requests
from geopy.distance import geodesic
from cachetools import TTLCache
from loguru import logger
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.config import settings
from app.models.appointment import Location


# Cache for travel times (key: (origin_lat, origin_lng, dest_lat, dest_lng), value: travel time in seconds)
travel_time_cache = TTLCache(maxsize=1000, ttl=settings.CACHE_TTL)

# OAuth 2.0 scopes for the Google Routes API
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']


def get_google_credentials():
    """
    Get OAuth 2.0 credentials for the Google Routes API.
    
    Returns:
        Credentials object for authenticating with the Google Routes API
    """
    creds = None
    token_file = "token.json"
    
    # Check if token.json exists (contains cached credentials)
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_info(
                json.load(open(token_file)), SCOPES
            )
        except Exception as e:
            logger.error(f"Error loading credentials from token file: {e}")
    
    # If credentials don't exist or are invalid, create new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing credentials: {e}")
                creds = None
        else:
            # In production, we should have a refresh token already
            # If not, log an error and fall back to API key
            logger.error("No valid credentials found. Using API key directly.")
            return None
        
        # Save credentials for future use
        if creds:
            with open(token_file, "w") as token:
                token.write(creds.to_json())
    
    return creds


def haversine_distance(origin: Location, destination: Location) -> float:
    """
    Calculate the great-circle distance between two points in kilometers using the haversine formula.
    This is a fallback method when the Google Routes API is not available.
    
    Args:
        origin: Origin location
        destination: Destination location
        
    Returns:
        Distance in kilometers
    """
    return geodesic(
        (origin.lat, origin.lng), 
        (destination.lat, destination.lng)
    ).kilometers


def estimate_travel_time_minutes(distance_km: float, avg_speed_kmh: float = 50.0) -> int:
    """
    Estimate travel time in minutes based on distance and average speed.
    This is a fallback method when the Google Routes API is not available.
    
    Args:
        distance_km: Distance in kilometers
        avg_speed_kmh: Average speed in kilometers per hour (default: 50 km/h)
        
    Returns:
        Estimated travel time in minutes
    """
    # Calculate travel time in hours, then convert to minutes
    travel_time_hours = distance_km / avg_speed_kmh
    return round(travel_time_hours * 60)


@lru_cache(maxsize=100)
def geocode_address(address: str) -> Optional[Location]:
    """
    Geocode an address to get latitude and longitude using Google Maps Geocoding API.
    
    Args:
        address: The address to geocode
        
    Returns:
        Location object with lat and lng, or None if geocoding failed
    """
    if not settings.GOOGLE_API_KEY:
        logger.warning("Google API key not set, cannot geocode address")
        return None
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": settings.GOOGLE_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "OK" and data["results"]:
            location = data["results"][0]["geometry"]["location"]
            return Location(
                lat=location["lat"],
                lng=location["lng"],
                address=address
            )
        else:
            logger.error(f"Geocoding failed: {data.get('status')} - {data.get('error_message', 'No error message')}")
            return None
    except Exception as e:
        logger.exception(f"Error geocoding address: {e}")
        return None


def get_travel_time_minutes(
    origin: Location, 
    destination: Location, 
    depart_time: Optional[str] = None
) -> int:
    """
    Get travel time in minutes between two locations using Google Routes Optimization API.
    Falls back to haversine distance estimation if API call fails.
    
    Args:
        origin: Origin location
        destination: Destination location
        depart_time: Departure time in RFC3339 format (optional)
        
    Returns:
        Travel time in minutes
    """
    # Check cache first
    cache_key = (origin.lat, origin.lng, destination.lat, destination.lng)
    if cache_key in travel_time_cache:
        return travel_time_cache[cache_key]
    
    # If no Google API key, use fallback method
    if not settings.GOOGLE_API_KEY:
        logger.warning("Google API key not set, using fallback distance calculation")
        distance_km = haversine_distance(origin, destination)
        travel_time = estimate_travel_time_minutes(distance_km)
        travel_time_cache[cache_key] = travel_time
        return travel_time
    
    # Get OAuth 2.0 credentials
    creds = get_google_credentials()
    
    # If credentials are not available, use fallback method
    if not creds:
        logger.warning("Google OAuth credentials not available, using fallback distance calculation")
        distance_km = haversine_distance(origin, destination)
        travel_time = estimate_travel_time_minutes(distance_km)
        travel_time_cache[cache_key] = travel_time
        return travel_time
    
    # Prepare request to Google Routes Optimization API
    url = settings.GOOGLE_ROUTES_API_BASE_URL
    
    # Get access token from credentials
    auth_req = Request()
    creds.refresh(auth_req)
    access_token = creds.token
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY
    }
    
    # Create a simple route optimization request with just two points
    payload = {
        "shipments": [
            {
                "deliveries": [
                    {
                        "arrivalLocation": {
                            "latLng": {
                                "latitude": destination.lat,
                                "longitude": destination.lng
                            }
                        }
                    }
                ],
                "pickups": [
                    {
                        "arrivalLocation": {
                            "latLng": {
                                "latitude": origin.lat,
                                "longitude": origin.lng
                            }
                        }
                    }
                ]
            }
        ],
        "vehicles": [
            {
                "startLocation": {
                    "latLng": {
                        "latitude": origin.lat,
                        "longitude": origin.lng
                    }
                },
                "endLocation": {
                    "latLng": {
                        "latitude": destination.lat,
                        "longitude": destination.lng
                    }
                }
            }
        ],
        "options": {
            "trafficMode": "TRAFFIC_AWARE"
        }
    }
    
    if depart_time:
        payload["options"]["departureTime"] = depart_time
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        # Extract travel time from the optimized route
        if "routes" in data and len(data["routes"]) > 0:
            route = data["routes"][0]
            travel_time_seconds = int(route["travelDuration"].replace("s", ""))
            travel_time_minutes = math.ceil(travel_time_seconds / 60)
            
            # Cache the result
            travel_time_cache[cache_key] = travel_time_minutes
            
            return travel_time_minutes
        else:
            logger.warning("No routes found in the response")
            raise ValueError("No routes found in the response")
            
    except Exception as e:
        logger.exception(f"Error getting travel time from Google Routes Optimization API: {e}")
        
        # Fall back to haversine distance
        distance_km = haversine_distance(origin, destination)
        travel_time = estimate_travel_time_minutes(distance_km)
        
        # Cache the fallback result
        travel_time_cache[cache_key] = travel_time
        
        return travel_time
