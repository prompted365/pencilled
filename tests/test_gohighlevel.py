import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.models.appointment import AppointmentCreate, Location
from app.services.gohighlevel import GoHighLevelService, GoHighLevelAPIError


class TestGoHighLevelService(unittest.TestCase):
    """Test cases for the GoHighLevelService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the requests module to avoid actual API calls
        self.requests_patcher = patch('app.services.gohighlevel.requests')
        self.mock_requests = self.requests_patcher.start()
        
        # Mock the geocode_address function
        self.geocode_patcher = patch('app.services.gohighlevel.geocode_address')
        self.mock_geocode = self.geocode_patcher.start()
        
        # Create service instance
        self.service = GoHighLevelService()
        
        # Set up test data
        self.test_location = Location(lat=40.7128, lng=-74.0060, address="123 Main St, New York, NY 10001")
        self.mock_geocode.return_value = self.test_location
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.requests_patcher.stop()
        self.geocode_patcher.stop()
    
    def test_get_appointments_success(self):
        """Test getting appointments successfully."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [
                {
                    "id": "event1",
                    "type": "appointment",
                    "title": "Test Appointment",
                    "startTime": "2025-03-16T10:00:00Z",
                    "endTime": "2025-03-16T11:00:00Z",
                    "durationInMinutes": 60,
                    "location": {
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "address": "123 Main St, New York, NY 10001"
                    },
                    "contactId": "contact1",
                    "calendarId": "cal1",
                    "locationId": "loc1"
                }
            ]
        }
        self.mock_requests.get.return_value = mock_response
        
        # Call the method
        appointments = self.service.get_appointments()
        
        # Assertions
        self.assertEqual(len(appointments), 1)
        self.assertEqual(appointments[0].id, "event1")
        self.assertEqual(appointments[0].title, "Test Appointment")
        self.assertEqual(appointments[0].duration_minutes, 60)
    
    def test_get_appointments_empty(self):
        """Test getting appointments when there are none."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}
        self.mock_requests.get.return_value = mock_response
        
        # Call the method
        appointments = self.service.get_appointments()
        
        # Assertions
        self.assertEqual(len(appointments), 0)
    
    def test_get_appointments_error(self):
        """Test getting appointments when API returns an error."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid request"}
        self.mock_requests.get.return_value = mock_response
        
        # Call the method
        appointments = self.service.get_appointments()
        
        # Assertions
        self.assertEqual(len(appointments), 0)
    
    def test_create_appointment_success(self):
        """Test creating an appointment successfully."""
        # Set up test data
        now = datetime.now()
        appointment_data = AppointmentCreate(
            lead_id="contact1",
            start_time=now,
            address="123 Main St, New York, NY 10001",
            duration_minutes=60,
            title="Test Appointment"
        )
        
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "new_appointment_id",
            "startTime": now.isoformat(),
            "endTime": (now + timedelta(minutes=60)).isoformat(),
            "title": "Test Appointment"
        }
        self.mock_requests.post.return_value = mock_response
        
        # Call the method
        response = self.service.create_appointment(appointment_data)
        
        # Assertions
        self.assertTrue(response.success)
        self.assertEqual(response.id, "new_appointment_id")
        self.assertEqual(response.title, "Test Appointment")
    
    def test_create_appointment_geocode_failure(self):
        """Test creating an appointment when geocoding fails."""
        # Set up test data
        now = datetime.now()
        appointment_data = AppointmentCreate(
            lead_id="contact1",
            start_time=now,
            address="Invalid Address",
            duration_minutes=60,
            title="Test Appointment"
        )
        
        # Set up mock geocode to fail
        self.mock_geocode.return_value = None
        
        # Call the method
        response = self.service.create_appointment(appointment_data)
        
        # Assertions
        self.assertFalse(response.success)
        self.assertEqual(response.id, "")
        self.assertIn("Could not geocode address", response.message)
    
    def test_create_appointment_api_error(self):
        """Test creating an appointment when API returns an error."""
        # Set up test data
        now = datetime.now()
        appointment_data = AppointmentCreate(
            lead_id="contact1",
            start_time=now,
            address="123 Main St, New York, NY 10001",
            duration_minutes=60,
            title="Test Appointment"
        )
        
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid request"}
        self.mock_requests.post.return_value = mock_response
        
        # Call the method
        response = self.service.create_appointment(appointment_data)
        
        # Assertions
        self.assertFalse(response.success)
        self.assertEqual(response.id, "")
        self.assertIn("GoHighLevel API error", response.message)


if __name__ == '__main__':
    unittest.main()
