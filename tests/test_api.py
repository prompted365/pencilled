import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.models.candidate_slot import AvailableSlot
from app.models.appointment import AppointmentResponse


class TestAPI(unittest.TestCase):
    """Test cases for the API endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        # Mock the AppointmentOptimizer
        self.optimizer_patcher = patch('app.api.routes.AppointmentOptimizer')
        self.mock_optimizer_class = self.optimizer_patcher.start()
        self.mock_optimizer = self.mock_optimizer_class.return_value
        
        # Mock the GoHighLevelService
        self.ghl_patcher = patch('app.api.routes.GoHighLevelService')
        self.mock_ghl_class = self.ghl_patcher.start()
        self.mock_ghl = self.mock_ghl_class.return_value
        
        # Set up test data
        now = datetime.now()
        self.test_slots = [
            AvailableSlot(
                start_time=now,
                end_time=now.replace(hour=now.hour + 1),
                efficiency_score=95.5
            ),
            AvailableSlot(
                start_time=now.replace(hour=now.hour + 2),
                end_time=now.replace(hour=now.hour + 3),
                efficiency_score=87.2
            )
        ]
        
        self.test_appointment_response = AppointmentResponse(
            id="new_appointment_id",
            start_time=now,
            end_time=now.replace(hour=now.hour + 1),
            title="Test Appointment",
            success=True,
            message="Appointment created successfully"
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.optimizer_patcher.stop()
        self.ghl_patcher.stop()
    
    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
    
    def test_get_available_slots(self):
        """Test getting available slots."""
        # Set up mock return value
        self.mock_optimizer.get_optimized_slots.return_value = self.test_slots
        
        # Make request
        response = self.client.get(
            "/api/slots",
            params={
                "lead_address": "123 Main St, New York, NY 10001",
                "appointment_duration": 60
            }
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["slots"]), 2)
        self.assertEqual(data["lead_address"], "123 Main St, New York, NY 10001")
        self.assertEqual(data["appointment_duration"], 60)
    
    def test_get_available_slots_error(self):
        """Test getting available slots when an error occurs."""
        # Set up mock to raise exception
        self.mock_optimizer.get_optimized_slots.side_effect = Exception("Test error")
        
        # Make request
        response = self.client.get(
            "/api/slots",
            params={
                "lead_address": "123 Main St, New York, NY 10001",
                "appointment_duration": 60
            }
        )
        
        # Assertions
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.json())
    
    def test_create_appointment(self):
        """Test creating an appointment."""
        # Set up mock return value
        self.mock_ghl.create_appointment.return_value = self.test_appointment_response
        
        # Make request
        response = self.client.post(
            "/api/appointments",
            json={
                "lead_id": "contact1",
                "start_time": datetime.now().isoformat(),
                "address": "123 Main St, New York, NY 10001",
                "duration_minutes": 60,
                "title": "Test Appointment"
            }
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "new_appointment_id")
        self.assertEqual(data["title"], "Test Appointment")
        self.assertTrue(data["success"])
    
    def test_create_appointment_failure(self):
        """Test creating an appointment when it fails."""
        # Set up mock return value
        failed_response = self.test_appointment_response.copy()
        failed_response.success = False
        failed_response.message = "Failed to create appointment"
        self.mock_ghl.create_appointment.return_value = failed_response
        
        # Make request
        response = self.client.post(
            "/api/appointments",
            json={
                "lead_id": "contact1",
                "start_time": datetime.now().isoformat(),
                "address": "123 Main St, New York, NY 10001",
                "duration_minutes": 60,
                "title": "Test Appointment"
            }
        )
        
        # Assertions
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())
    
    def test_create_appointment_error(self):
        """Test creating an appointment when an error occurs."""
        # Set up mock to raise exception
        self.mock_ghl.create_appointment.side_effect = Exception("Test error")
        
        # Make request
        response = self.client.post(
            "/api/appointments",
            json={
                "lead_id": "contact1",
                "start_time": datetime.now().isoformat(),
                "address": "123 Main St, New York, NY 10001",
                "duration_minutes": 60,
                "title": "Test Appointment"
            }
        )
        
        # Assertions
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.json())


if __name__ == '__main__':
    unittest.main()
