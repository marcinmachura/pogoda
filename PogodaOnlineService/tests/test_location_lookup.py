#!/usr/bin/env python3
"""Unit tests for climate location lookup functionality."""

import unittest
import tempfile
import pickle
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.append('.')

from app.climate.geocode import GeocodingService, GeoLocation, GeocodeError
from app.climate.models import CompactClimateModel, load_compact_climate_model
from app.climate.service import ClimateService


class TestGeocodingService(unittest.TestCase):
    """Test the geocoding service."""
    
    def setUp(self):
        self.geocoding_service = GeocodingService()
    
    @patch('requests.Session.get')
    def test_successful_geocoding(self, mock_get):
        """Test successful geocoding of a city."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'lat': '51.5074456',
                'lon': '-0.1277653',
                'display_name': 'London, Greater London, England, United Kingdom',
                'address': {
                    'country': 'United Kingdom'
                }
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test geocoding
        result = self.geocoding_service.geocode("London")
        
        # Assertions
        self.assertIsInstance(result, GeoLocation)
        self.assertEqual(result.city, "London")
        self.assertAlmostEqual(result.latitude, 51.5074456, places=6)
        self.assertAlmostEqual(result.longitude, -0.1277653, places=6)
        self.assertEqual(result.country, "United Kingdom")
        self.assertIn("London", result.display_name)
    
    @patch('requests.Session.get')
    def test_no_results_geocoding(self, mock_get):
        """Test geocoding when no results are found."""
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test geocoding
        with self.assertRaises(GeocodeError) as cm:
            self.geocoding_service.geocode("NonexistentCity")
        
        self.assertIn("No geocoding results found", str(cm.exception))
    
    @patch('requests.Session.get')
    def test_request_exception(self, mock_get):
        """Test geocoding when request fails."""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")
        
        with self.assertRaises(GeocodeError) as cm:
            self.geocoding_service.geocode("London")
        
        self.assertIn("Geocoding request failed", str(cm.exception))


class TestCompactClimateModel(unittest.TestCase):
    """Test the CompactClimateModel."""
    
    def setUp(self):
        """Create a test climate model."""
        # Create sample data
        location_map = {
            (np.float32(51.5), np.float32(-0.1)): 0,    # London-ish
            (np.float32(40.7), np.float32(-74.0)): 25,  # NYC-ish
            (np.float32(-33.9), np.float32(18.4)): 50,  # Cape Town-ish
        }
        
        # Create sample climate data
        # Format: [year_count, year1, 12_temps*100, 12_precips*10, year2, ...]
        data = []
        
        # London data (index 0)
        data.extend([2])  # 2 years of data
        # Year 2020
        data.extend([2020])
        data.extend([500, 600, 800, 1200, 1600, 2000, 2200, 2100, 1700, 1300, 800, 600])  # temps * 100
        data.extend([50, 40, 45, 55, 60, 65, 40, 50, 65, 70, 60, 55])  # precip * 10
        # Year 2021
        data.extend([2021])
        data.extend([480, 580, 780, 1180, 1580, 1980, 2180, 2080, 1680, 1280, 780, 580])
        data.extend([52, 42, 47, 57, 62, 67, 42, 52, 67, 72, 62, 57])
        
        # NYC data (index 25)
        data.extend([1])  # 1 year of data
        data.extend([2020])
        data.extend([0, 200, 600, 1200, 1800, 2400, 2700, 2600, 2000, 1400, 800, 300])
        data.extend([80, 70, 90, 100, 110, 120, 110, 100, 90, 80, 70, 75])
        
        # Cape Town data (index 50)
        data.extend([1])
        data.extend([2020])
        data.extend([2000, 2200, 1800, 1400, 1000, 800, 800, 1000, 1200, 1600, 1800, 2000])
        data.extend([20, 15, 25, 50, 80, 120, 100, 80, 40, 30, 25, 20])
        
        np_data = np.array(data, dtype=np.float32)
        
        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        with open(self.temp_file.name, 'wb') as f:
            pickle.dump((location_map, np_data), f)
        
        self.model = CompactClimateModel(Path(self.temp_file.name))
    
    def tearDown(self):
        """Clean up test file with Windows retry to avoid PermissionError."""
        path = Path(self.temp_file.name)
        if path.exists():
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                import time
                time.sleep(0.1)
                try:
                    path.unlink(missing_ok=True)
                except PermissionError:
                    # Leave file; test environment limitation.
                    pass
    
    def test_exact_location_data_extraction(self):
        """Test extracting data for an exact location match."""
        temp_dict, precip_dict = self.model.extract_data(51.5, -0.1, [2020, 2021])
        
        # Check that we got data for both years
        self.assertEqual(set(temp_dict.keys()), {2020, 2021})
        self.assertEqual(set(precip_dict.keys()), {2020, 2021})
        
        # Check 2020 data
        self.assertEqual(len(temp_dict[2020]), 12)  # 12 months
        self.assertEqual(len(precip_dict[2020]), 12)
        
        # Check temperature conversion (stored as *100)
        self.assertAlmostEqual(temp_dict[2020][0], 5.0, places=1)  # 500/100
        self.assertAlmostEqual(temp_dict[2020][6], 22.0, places=1)  # 2200/100
        
        # Check precipitation conversion (stored as *10)
        self.assertAlmostEqual(precip_dict[2020][0], 5.0, places=1)  # 50/10
        self.assertAlmostEqual(precip_dict[2020][6], 4.0, places=1)  # 40/10
    
    def test_nonexistent_location(self):
        """Test that nonexistent locations raise KeyError."""
        with self.assertRaises(KeyError):
            self.model.extract_data(0.0, 0.0, [2020])
    
    def test_find_closest_location(self):
        """Test finding the closest location."""
        # Test point close to London (51.5, -0.1)
        closest_lat, closest_lon, distance = self.model.find_closest_location(51.6, -0.2)
        
        self.assertAlmostEqual(closest_lat, 51.5, places=1)
        self.assertAlmostEqual(closest_lon, -0.1, places=1)
        self.assertLess(distance, 50)  # Should be less than 50km away
    
    def test_find_closest_location_far_point(self):
        """Test finding closest location for a point far from all locations."""
        # Point in the middle of the Pacific Ocean
        closest_lat, closest_lon, distance = self.model.find_closest_location(0.0, 180.0)
        
        # Should still find a closest location
        self.assertIsInstance(closest_lat, float)
        self.assertIsInstance(closest_lon, float)
        self.assertGreater(distance, 1000)  # Should be far away
    
    def test_empty_location_map(self):
        """Test behavior with empty location map."""
        # Create model with empty location map
        empty_map = {}
        empty_data = np.array([], dtype=np.float32)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        with open(temp_file.name, 'wb') as f:
            pickle.dump((empty_map, empty_data), f)
        
        try:
            model = CompactClimateModel(Path(temp_file.name))
            with self.assertRaises(ValueError):
                model.find_closest_location(51.5, -0.1)
        finally:
            # Robust cleanup with retry for Windows
            temp_path = Path(temp_file.name)
            if temp_path.exists():
                try:
                    temp_path.unlink(missing_ok=True)
                except PermissionError:
                    import time
                    time.sleep(0.1)
                    try:
                        temp_path.unlink(missing_ok=True)
                    except PermissionError:
                        pass


class TestClimateService(unittest.TestCase):
    """Test the ClimateService integration."""
    
    @patch('app.climate.service.GeocodingService')
    @patch('app.climate.service.load_compact_climate_model')
    @patch('app.climate.service.get_settings')
    def test_get_aggregated_climate_data(self, mock_settings, mock_load_model, mock_geocoding_class):
        """Test the aggregated climate data endpoint."""
        # Setup mocks
        mock_settings.return_value.active_model_path = Path("fake/path.pkl")
        
        # Mock geocoding
        mock_geocoding = Mock()
        mock_location = GeoLocation(
            city="London",
            latitude=51.5,
            longitude=-0.1,
            country="UK",
            display_name="London, UK"
        )
        mock_geocoding.geocode.return_value = mock_location
        mock_geocoding_class.return_value = mock_geocoding
        
        # Mock climate model
        mock_model = Mock()
        mock_model.find_closest_location.return_value = (51.5, -0.1, 10.5)
        mock_model.extract_data.return_value = (
            {2020: [5.0, 6.0, 8.0, 12.0, 16.0, 20.0, 22.0, 21.0, 17.0, 13.0, 8.0, 6.0]},
            {2020: [5.0, 4.0, 4.5, 5.5, 6.0, 6.5, 4.0, 5.0, 6.5, 7.0, 6.0, 5.5]}
        )
        mock_load_model.return_value = mock_model
        
        # Create service and test
        service = ClimateService()
        location, temps, precips, classification, distance = service.get_aggregated_climate_data(
            "London", [2020]
        )
        
        # Assertions
        self.assertEqual(location.city, "London")
        self.assertEqual(len(temps), 12)
        self.assertEqual(len(precips), 12)
        self.assertAlmostEqual(distance, 10.5)
        self.assertIsNotNone(classification)
    
    @patch('app.climate.service.GeocodingService')
    def test_geocoding_failure(self, mock_geocoding_class):
        """Test handling of geocoding failures."""
        # Mock geocoding failure
        mock_geocoding = Mock()
        mock_geocoding.geocode.side_effect = GeocodeError("City not found")
        mock_geocoding_class.return_value = mock_geocoding
        
        service = ClimateService()
        
        with self.assertRaises(ValueError) as cm:
            service.get_aggregated_climate_data("NonexistentCity", [2020])
        
        self.assertIn("Could not find location", str(cm.exception))


class TestClimateModelCaching(unittest.TestCase):
    """Test the climate model caching functionality."""
    
    def setUp(self):
        # Clear any cached model
        import app.climate.models
        app.climate.models._cached_compact_model = None
        app.climate.models._cached_path = None
    
    def test_model_caching(self):
        """Test that the model is properly cached."""
        # Create a temporary test file
        location_map = {(np.float32(51.5), np.float32(-0.1)): 0}
        data = np.array([1, 2020] + [100] * 12 + [10] * 12, dtype=np.float32)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        with open(temp_file.name, 'wb') as f:
            pickle.dump((location_map, data), f)
        
        try:
            path = Path(temp_file.name)
            
            # Load model first time
            model1 = load_compact_climate_model(path)
            
            # Load model second time (should be cached)
            model2 = load_compact_climate_model(path)
            
            # Should be the same instance
            self.assertIs(model1, model2)
            
        finally:
            temp_path = Path(temp_file.name)
            if temp_path.exists():
                try:
                    temp_path.unlink(missing_ok=True)
                except PermissionError:
                    import time
                    time.sleep(0.1)
                    try:
                        temp_path.unlink(missing_ok=True)
                    except PermissionError:
                        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)