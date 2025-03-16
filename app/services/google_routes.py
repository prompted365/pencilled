from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import math

import requests
from loguru import logger
from google.auth.transport.requests import Request

from app.config import settings
from app.models.appointment import Location
from app.utils.distance_utils import get_travel_time_minutes, geocode_address, get_google_credentials


class GoogleRoutesService:
    """Service for interacting with the Google Routes Optimization API."""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.base_url = settings.GOOGLE_ROUTES_API_BASE_URL
        
        if not self.api_key:
            logger.warning("Google API key not set")
    
    def get_travel_time(
        self, 
        origin: Location, 
        destination: Location, 
        depart_time: Optional[datetime] = None
    ) -> int:
        """
        Get travel time in minutes between two locations.
        
        Args:
            origin: Origin location
            destination: Destination location
            depart_time: Departure time (optional)
            
        Returns:
            Travel time in minutes
        """
        depart_time_str = None
        if depart_time:
            depart_time_str = depart_time.isoformat()
        
        return get_travel_time_minutes(origin, destination, depart_time_str)
    
    def get_travel_times_matrix(
        self, 
        locations: List[Location], 
        depart_time: Optional[datetime] = None
    ) -> List[List[int]]:
        """
        Get a matrix of travel times between multiple locations using the Google Routes Optimization API.
        
        Args:
            locations: List of locations
            depart_time: Departure time (optional)
            
        Returns:
            Matrix of travel times in minutes (matrix[i][j] is travel time from locations[i] to locations[j])
        """
        if not self.api_key:
            logger.warning("Google API key not set, using fallback distance calculation")
            # Use the utility function to calculate travel times
            matrix = []
            for origin in locations:
                row = []
                for destination in locations:
                    if origin == destination:
                        row.append(0)  # No travel time to same location
                    else:
                        travel_time = get_travel_time_minutes(origin, destination)
                        row.append(travel_time)
                matrix.append(row)
            return matrix
        
        # Get OAuth 2.0 credentials
        creds = get_google_credentials()
        
        # If credentials are not available, use fallback method
        if not creds:
            logger.warning("Google OAuth credentials not available, using fallback distance calculation")
            matrix = []
            for origin in locations:
                row = []
                for destination in locations:
                    if origin == destination:
                        row.append(0)  # No travel time to same location
                    else:
                        travel_time = get_travel_time_minutes(origin, destination)
                        row.append(travel_time)
                matrix.append(row)
            return matrix
        
        # Get access token from credentials
        auth_req = Request()
        creds.refresh(auth_req)
        access_token = creds.token
        
        # Prepare request to Google Routes Optimization API
        url = self.base_url
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-Goog-Api-Key": self.api_key
        }
        
        # Create a route optimization request with multiple locations
        # We'll create a shipment for each pair of locations to get the travel times
        shipments = []
        vehicles = []
        
        # Add a vehicle starting at each location
        for i, location in enumerate(locations):
            vehicles.append({
                "startLocation": {
                    "latLng": {
                        "latitude": location.lat,
                        "longitude": location.lng
                    }
                },
                "endLocation": {
                    "latLng": {
                        "latitude": location.lat,
                        "longitude": location.lng
                    }
                },
                "vehicleIndex": i
            })
        
        # Add a shipment for each pair of locations
        for i, origin in enumerate(locations):
            for j, destination in enumerate(locations):
                if i != j:  # Skip same location
                    shipments.append({
                        "deliveries": [
                            {
                                "arrivalLocation": {
                                    "latLng": {
                                        "latitude": destination.lat,
                                        "longitude": destination.lng
                                    }
                                },
                                "tags": [f"dest_{j}"]
                            }
                        ],
                        "pickups": [
                            {
                                "arrivalLocation": {
                                    "latLng": {
                                        "latitude": origin.lat,
                                        "longitude": origin.lng
                                    }
                                },
                                "tags": [f"origin_{i}"]
                            }
                        ],
                        "shipmentIndex": i * len(locations) + j
                    })
        
        payload = {
            "shipments": shipments,
            "vehicles": vehicles,
            "options": {
                "trafficMode": "TRAFFIC_AWARE"
            }
        }
        
        if depart_time:
            payload["options"]["departureTime"] = depart_time.isoformat()
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            
            # Initialize matrix with zeros
            n = len(locations)
            matrix = [[0 for _ in range(n)] for _ in range(n)]
            
            # Extract travel times from the optimized routes
            if "routes" in data:
                for route in data["routes"]:
                    # Extract vehicle index to determine the origin
                    vehicle_idx = route.get("vehicleIndex", 0)
                    
                    # Extract travel times from visits
                    for visit in route.get("visits", []):
                        # Get the shipment index to determine the destination
                        shipment_idx = visit.get("shipmentIndex", 0)
                        dest_idx = shipment_idx % n
                        
                        # Extract travel time
                        travel_time_seconds = int(visit.get("travelDuration", "0s").replace("s", ""))
                        travel_time_minutes = math.ceil(travel_time_seconds / 60)
                        
                        # Add to matrix
                        matrix[vehicle_idx][dest_idx] = travel_time_minutes
            
            # Fill in any missing values using individual calculations
            for i in range(n):
                for j in range(n):
                    if i != j and matrix[i][j] == 0:
                        matrix[i][j] = get_travel_time_minutes(locations[i], locations[j])
            
            return matrix
        except Exception as e:
            logger.exception(f"Error getting travel time matrix from Google Routes Optimization API: {e}")
            
            # Fall back to individual calculations
            matrix = []
            for origin in locations:
                row = []
                for destination in locations:
                    if origin == destination:
                        row.append(0)  # No travel time to same location
                    else:
                        travel_time = get_travel_time_minutes(origin, destination)
                        row.append(travel_time)
                matrix.append(row)
            return matrix
    
    def geocode_address(self, address: str) -> Optional[Location]:
        """
        Geocode an address to get latitude and longitude.
        
        Args:
            address: The address to geocode
            
        Returns:
            Location object with lat and lng, or None if geocoding failed
        """
        return geocode_address(address)
