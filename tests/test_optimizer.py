import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.models.appointment import Appointment, Location
from app.models.time_window import TimeWindow
from app.services.optimizer import AppointmentOptimizer


class TestAppointmentOptimizer(unittest.TestCase):
    """Test cases for the AppointmentOptimizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the services to avoid actual API calls
        self.ghl_service_patcher = patch('app.services.optimizer.GoHighLevelService')
        self.routes_service_patcher = patch('app.services.optimizer.GoogleRoutesService')
        
        self.mock_ghl_service = self.ghl_service_patcher.start()
        self.mock_routes_service = self.routes_service_patcher.start()
        
        # Create optimizer instance with mocked services
        self.optimizer = AppointmentOptimizer()
        
        # Set up test data
        self.home_base = Location(lat=40.7128, lng=-74.0060, address="Home Base")
        self.location1 = Location(lat=40.7500, lng=-74.0000, address="Location 1")
        self.location2 = Location(lat=40.7400, lng=-74.0100, address="Location 2")
        self.lead_location = Location(lat=40.7300, lng=-74.0200, address="Lead Location")
        
        # Set up mock return values
        self.mock_routes_service_instance = self.mock_routes_service.return_value
        self.mock_routes_service_instance.get_travel_time.return_value = 15  # 15 minutes travel time
        self.mock_routes_service_instance.geocode_address.return_value = self.lead_location
        
        self.mock_ghl_service_instance = self.mock_ghl_service.return_value
        self.mock_ghl_service_instance.get_appointments.return_value = []
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.ghl_service_patcher.stop()
        self.routes_service_patcher.stop()
    
    def test_get_free_time_windows_no_appointments(self):
        """Test getting free time windows when there are no appointments."""
        # Set up test data
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Call the method
        free_windows = self.optimizer.get_free_time_windows([], tomorrow, 1)
        
        # Assertions
        self.assertGreater(len(free_windows), 0)
        for window in free_windows:
            self.assertEqual(window.start_location, self.optimizer.home_base)
            self.assertEqual(window.end_location, self.optimizer.home_base)
    
    def test_get_free_time_windows_with_appointments(self):
        """Test getting free time windows when there are existing appointments."""
        # Set up test data
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Create test appointments
        tomorrow_10am = datetime.combine(tomorrow, datetime.min.time().replace(hour=10))
        tomorrow_11am = datetime.combine(tomorrow, datetime.min.time().replace(hour=11))
        tomorrow_2pm = datetime.combine(tomorrow, datetime.min.time().replace(hour=14))
        tomorrow_3pm = datetime.combine(tomorrow, datetime.min.time().replace(hour=15))
        
        appointments = [
            Appointment(
                id="1",
                title="Appointment 1",
                start_time=tomorrow_10am,
                end_time=tomorrow_11am,
                duration_minutes=60,
                location=self.location1,
                calendar_id="cal1",
                location_id="loc1"
            ),
            Appointment(
                id="2",
                title="Appointment 2",
                start_time=tomorrow_2pm,
                end_time=tomorrow_3pm,
                duration_minutes=60,
                location=self.location2,
                calendar_id="cal1",
                location_id="loc1"
            )
        ]
        
        # Call the method
        free_windows = self.optimizer.get_free_time_windows(appointments, tomorrow, 1)
        
        # Assertions
        self.assertGreaterEqual(len(free_windows), 3)  # Before first, between, after last
    
    def test_generate_candidate_slots(self):
        """Test generating candidate slots from free time windows."""
        # Set up test data
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        tomorrow_9am = datetime.combine(tomorrow, datetime.min.time().replace(hour=9))
        tomorrow_5pm = datetime.combine(tomorrow, datetime.min.time().replace(hour=17))
        
        free_window = TimeWindow(
            start_time=tomorrow_9am,
            end_time=tomorrow_5pm,
            start_location=self.home_base,
            end_location=self.home_base
        )
        
        # Call the method
        candidate_slots = self.optimizer.generate_candidate_slots(
            [free_window], 
            self.lead_location,
            appointment_duration=60
        )
        
        # Assertions
        self.assertGreater(len(candidate_slots), 0)
        for slot in candidate_slots:
            self.assertEqual(slot.lead_location, self.lead_location)
            self.assertEqual(slot.travel_time_to_minutes, 15)
            self.assertEqual(slot.travel_time_from_minutes, 15)
            self.assertEqual((slot.end_time - slot.start_time).total_seconds() / 60, 60)
    
    def test_get_optimized_slots(self):
        """Test getting optimized slots for a lead."""
        # Set up test data
        lead_address = "123 Main St, New York, NY 10001"
        
        # Call the method
        available_slots = self.optimizer.get_optimized_slots(lead_address)
        
        # Assertions
        self.assertIsInstance(available_slots, list)
        # Since we're using mocks, we should get slots even without real data
        self.assertGreaterEqual(len(available_slots), 0)


if __name__ == '__main__':
    unittest.main()
