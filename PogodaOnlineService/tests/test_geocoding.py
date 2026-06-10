"""Unit tests for geocoding functionality."""

import pytest
from unittest.mock import Mock, patch
import requests

from app.climate.geocode import GeocodingService, GeoLocation, GeocodeError


class TestGeocodingService:
    """Test cases for the GeocodingService class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.geocoding_service = GeocodingService()

    @patch('requests.Session.get')
    def test_successful_geocoding(self, mock_get):
        """Test successful geocoding of a city name."""
        # Arrange
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

        # Act
        result = self.geocoding_service.geocode("London")

        # Assert
        assert isinstance(result, GeoLocation)
        assert result.city == "London"
        assert abs(result.latitude - 51.5074456) < 0.0001
        assert abs(result.longitude - (-0.1277653)) < 0.0001
        assert result.country == "United Kingdom"
        assert "London" in result.display_name
        
        # Verify the API call was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert 'q' in call_args[1]['params']
        assert call_args[1]['params']['q'] == "London"
        assert call_args[1]['params']['format'] == 'json'

    @patch('requests.Session.get')
    def test_geocoding_no_results(self, mock_get):
        """Test geocoding when no results are returned."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []  # Empty results
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(GeocodeError, match="No geocoding results found for: NonexistentCity"):
            self.geocoding_service.geocode("NonexistentCity")

    @patch('requests.Session.get')
    def test_geocoding_network_error(self, mock_get):
        """Test geocoding when network request fails."""
        # Arrange
        mock_get.side_effect = requests.RequestException("Network error")

        # Act & Assert
        with pytest.raises(GeocodeError, match="Geocoding request failed"):
            self.geocoding_service.geocode("London")

    @patch('requests.Session.get')
    def test_geocoding_invalid_response(self, mock_get):
        """Test geocoding when response has invalid format."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                # Missing required 'lat' field
                'lon': '-0.1277653',
                'display_name': 'London, Greater London, England, United Kingdom'
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(GeocodeError, match="Failed to parse geocoding response"):
            self.geocoding_service.geocode("London")

    @patch('requests.Session.get')
    def test_geocoding_http_error(self, mock_get):
        """Test geocoding when HTTP error occurs."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(GeocodeError, match="Geocoding request failed"):
            self.geocoding_service.geocode("London")

    def test_geolocation_dataclass(self):
        """Test GeoLocation dataclass functionality."""
        # Arrange & Act
        location = GeoLocation(
            city="Test City",
            latitude=12.34,
            longitude=56.78,
            country="Test Country",
            display_name="Test City, Test Country"
        )

        # Assert
        assert location.city == "Test City"
        assert location.latitude == 12.34
        assert location.longitude == 56.78
        assert location.country == "Test Country"
        assert location.display_name == "Test City, Test Country"

    def test_geolocation_dataclass_minimal(self):
        """Test GeoLocation dataclass with minimal required fields."""
        # Arrange & Act
        location = GeoLocation(
            city="Test City",
            latitude=12.34,
            longitude=56.78
        )

        # Assert
        assert location.city == "Test City"
        assert location.latitude == 12.34
        assert location.longitude == 56.78
        assert location.country is None
        assert location.display_name is None

    @pytest.mark.parametrize("city_name,expected_query", [
        ("London", "London"),
        ("New York", "New York"),
        ("Sao Paulo", "Sao Paulo"),
        ("Beijing", "Beijing"),  # Beijing in English
    ])
    @patch('requests.Session.get')
    def test_geocoding_various_city_names(self, mock_get, city_name, expected_query):
        """Test geocoding with various city name formats."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'lat': '0.0',
                'lon': '0.0',
                'display_name': f'{city_name}, Country',
                'address': {'country': 'Country'}
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = self.geocoding_service.geocode(city_name)

        # Assert
        assert result.city == city_name
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['q'] == expected_query