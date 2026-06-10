"""Integration tests for the ClimateService class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.climate.service import ClimateService
from app.climate.geocode import GeoLocation, GeocodeError
from app.climate.models import ClimateClassification


class TestClimateServiceIntegration:
    """Integration tests for ClimateService."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.service = ClimateService()

    @patch('app.climate.service.get_settings')
    @patch('app.climate.service.load_compact_climate_model')
    @patch.object(ClimateService, '_classify_climate')
    def test_get_aggregated_climate_data_success(self, mock_classify, mock_load_model, mock_settings):
        """Test successful aggregated climate data retrieval."""
        # Arrange
        mock_settings.return_value.active_model_path = Path("fake/path.pkl")
        
        # Mock geocoding (this will use the real geocoding service)
        mock_location = GeoLocation(
            city="London",
            latitude=51.5074456,
            longitude=-0.1277653,
            country="United Kingdom",
            display_name="London, Greater London, England, United Kingdom"
        )
        
        # Mock climate model
        mock_model = Mock()
        mock_model.find_closest_location.return_value = (51.5, -0.1, 10.5)
        mock_model.extract_data.return_value = (
            {
                2020: [5.0, 6.0, 8.0, 12.0, 16.0, 20.0, 22.0, 21.0, 17.0, 13.0, 8.0, 6.0],
                2021: [4.8, 5.8, 7.8, 11.8, 15.8, 19.8, 21.8, 20.8, 16.8, 12.8, 7.8, 5.8]
            },
            {
                2020: [5.0, 4.0, 4.5, 5.5, 6.0, 6.5, 4.0, 5.0, 6.5, 7.0, 6.0, 5.5],
                2021: [5.2, 4.2, 4.7, 5.7, 6.2, 6.7, 4.2, 5.2, 6.7, 7.2, 6.2, 5.7]
            }
        )
        mock_load_model.return_value = mock_model
        
        # Mock classification
        mock_classification = ClimateClassification(
            koppen_code="Cfb",
            koppen_name="Oceanic",
            trewartha_code="Do",
            trewartha_name="Oceanic"
        )
        mock_classify.return_value = mock_classification
        
        # Mock geocoding to return our test location
        with patch.object(self.service.geocoding_service, 'geocode', return_value=mock_location):
            # Act
            location, temps, precips, classification, distance = self.service.get_aggregated_climate_data(
                "London", [2020, 2021]
            )

        # Assert
        assert location.city == "London"
        assert location.latitude == 51.5074456
        assert len(temps) == 12  # 12 months
        assert len(precips) == 12  # 12 months
        assert abs(distance - 10.5) < 0.1
        assert classification.koppen_code == "Cfb"
        assert classification.trewartha_code == "Do"
        
        # Check that temperatures are averaged correctly
        # Month 0: (5.0 + 4.8) / 2 = 4.9
        assert abs(temps[0] - 4.9) < 0.1
        # Month 6: (22.0 + 21.8) / 2 = 21.9
        assert abs(temps[6] - 21.9) < 0.1

    @patch('app.climate.service.get_settings')
    @patch('app.climate.service.load_compact_climate_model')
    @patch.object(ClimateService, '_classify_climate')
    def test_get_yearly_climate_data_success(self, mock_classify, mock_load_model, mock_settings):
        """Test successful yearly climate data retrieval."""
        # Arrange
        mock_settings.return_value.active_model_path = Path("fake/path.pkl")
        
        mock_location = GeoLocation(
            city="London",
            latitude=51.5074456,
            longitude=-0.1277653,
            country="United Kingdom",
            display_name="London, Greater London, England, United Kingdom"
        )
        
        # Mock climate model
        mock_model = Mock()
        mock_model.find_closest_location.return_value = (51.5, -0.1, 10.5)
        mock_model.extract_data.return_value = (
            {
                2020: [5.0, 6.0, 8.0, 12.0, 16.0, 20.0, 22.0, 21.0, 17.0, 13.0, 8.0, 6.0],
                2021: [4.8, 5.8, 7.8, 11.8, 15.8, 19.8, 21.8, 20.8, 16.8, 12.8, 7.8, 5.8]
            },
            {
                2020: [5.0, 4.0, 4.5, 5.5, 6.0, 6.5, 4.0, 5.0, 6.5, 7.0, 6.0, 5.5],
                2021: [5.2, 4.2, 4.7, 5.7, 6.2, 6.7, 4.2, 5.2, 6.7, 7.2, 6.2, 5.7]
            }
        )
        mock_load_model.return_value = mock_model
        
        # Mock classification for different years
        def classify_side_effect(temps, precips, lat):
            if temps[0] > 4.9:  # 2020 data
                return ClimateClassification("Cfb", "Oceanic", "Do", "Oceanic")
            else:  # 2021 data
                return ClimateClassification("Cfa", "Humid subtropical", "Cf", "Subtropical")
        
        mock_classify.side_effect = classify_side_effect
        
        # Mock geocoding
        with patch.object(self.service.geocoding_service, 'geocode', return_value=mock_location):
            # Act
            location, year_classifications, distance = self.service.get_yearly_climate_data(
                "London", [2020, 2021]
            )

        # Assert
        assert location.city == "London"
        assert len(year_classifications) == 2
        assert 2020 in year_classifications
        assert 2021 in year_classifications
        assert year_classifications[2020].koppen_code == "Cfb"
        assert year_classifications[2021].koppen_code == "Cfa"
        assert abs(distance - 10.5) < 0.1

    def test_geocoding_failure(self):
        """Test handling of geocoding failures."""
        # Mock geocoding failure
        with patch.object(self.service.geocoding_service, 'geocode', side_effect=GeocodeError("City not found")):
            # Act & Assert
            with pytest.raises(ValueError, match="Could not find location for city: NonexistentCity"):
                self.service.get_aggregated_climate_data("NonexistentCity", [2020])

    @patch('app.climate.service.get_settings')
    @patch('app.climate.service.load_compact_climate_model')
    def test_climate_model_data_extraction_failure(self, mock_load_model, mock_settings):
        """Test handling when climate model data extraction fails."""
        # Arrange
        mock_settings.return_value.active_model_path = Path("fake/path.pkl")
        
        mock_location = GeoLocation("London", 51.5, -0.1)
        
        # Mock climate model that raises KeyError
        mock_model = Mock()
        mock_model.find_closest_location.return_value = (51.5, -0.1, 10.5)
        mock_model.extract_data.side_effect = KeyError("No data for location")
        mock_load_model.return_value = mock_model
        
        # Mock geocoding to succeed
        with patch.object(self.service.geocoding_service, 'geocode', return_value=mock_location):
            # Act & Assert
            with pytest.raises(ValueError, match="Could not retrieve climate data"):
                self.service.get_aggregated_climate_data("London", [2020])

    @pytest.mark.parametrize("years", [
        [2020],
        [2020, 2021],
        [2018, 2019, 2020, 2021, 2022],
        [2000],  # Single old year
    ])
    @patch('app.climate.service.get_settings')
    @patch('app.climate.service.load_compact_climate_model')
    @patch.object(ClimateService, '_classify_climate')
    def test_various_year_ranges(self, mock_classify, mock_load_model, mock_settings, years):
        """Test service with various year ranges."""
        # Arrange
        mock_settings.return_value.active_model_path = Path("fake/path.pkl")
        
        mock_location = GeoLocation("London", 51.5, -0.1)
        
        # Create mock data for all requested years
        temp_data = {}
        precip_data = {}
        for year in years:
            temp_data[year] = [10.0] * 12  # Simple constant temperature
            precip_data[year] = [5.0] * 12   # Simple constant precipitation
        
        mock_model = Mock()
        mock_model.find_closest_location.return_value = (51.5, -0.1, 10.5)
        mock_model.extract_data.return_value = (temp_data, precip_data)
        mock_load_model.return_value = mock_model
        
        mock_classification = ClimateClassification("Cfb", "Oceanic", "Do", "Oceanic")
        mock_classify.return_value = mock_classification
        
        # Mock geocoding
        with patch.object(self.service.geocoding_service, 'geocode', return_value=mock_location):
            # Act
            location, temps, precips, classification, distance = self.service.get_aggregated_climate_data(
                "London", years
            )

        # Assert
        assert location.city == "London"
        assert len(temps) == 12
        assert len(precips) == 12
        assert all(abs(t - 10.0) < 0.1 for t in temps)  # All temperatures should be 10.0
        assert all(abs(p - 5.0) < 0.1 for p in precips)  # All precipitation should be 5.0


class TestClimateServiceClassification:
    """Test the climate classification functionality in ClimateService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ClimateService()

    @patch('app.climate.service.classify_koppen')
    @patch('app.climate.service.classify_trewartha')
    def test_successful_classification(self, mock_trewartha, mock_koppen):
        """Test successful climate classification."""
        # Arrange
        mock_koppen.return_value = ("Cfb", {"description": "Oceanic"})
        mock_trewartha.return_value = ("Do", {"description": "Oceanic"})
        
        temps = [5.0, 6.0, 8.0, 12.0, 16.0, 20.0, 22.0, 21.0, 17.0, 13.0, 8.0, 6.0]
        precips = [5.0, 4.0, 4.5, 5.5, 6.0, 6.5, 4.0, 5.0, 6.5, 7.0, 6.0, 5.5]
        latitude = 51.5

        # Act
        result = self.service._classify_climate(temps, precips, latitude)

        # Assert
        assert result.koppen_code == "Cfb"
        assert result.koppen_name == "Oceanic"
        assert result.trewartha_code == "Do"
        assert result.trewartha_name == "Oceanic"

    @patch('app.climate.service.classify_koppen')
    @patch('app.climate.service.classify_trewartha')
    def test_classification_fallback(self, mock_trewartha, mock_koppen):
        """Test climate classification fallback when classifiers fail."""
        from app.climate.classifiers import ClassificationError
        
        # Arrange
        mock_koppen.side_effect = ClassificationError("Invalid data")
        mock_trewartha.side_effect = ClassificationError("Invalid data")
        
        temps = [15.0] * 12  # Constant temperature
        precips = [50.0] * 12  # Constant precipitation
        latitude = 45.0

        # Act
        result = self.service._classify_climate(temps, precips, latitude)

        # Assert - Should fall back to simple classification
        assert result.koppen_code in ["Tropical", "Temperate-Wet", "Temperate-Dry", "Continental", "Polar"]
        assert result.trewartha_code in ["Tropical", "Temperate-Wet", "Temperate-Dry", "Continental", "Polar"]

    def test_simple_classification_logic(self):
        """Test the simple climate classification logic."""
        # Test tropical
        result = self.service._simple_classify(27.0, 1500.0)
        assert result == "Tropical"
        
        # Test temperate wet
        result = self.service._simple_classify(18.0, 1200.0)
        assert result == "Temperate-Wet"
        
        # Test temperate dry
        result = self.service._simple_classify(18.0, 800.0)
        assert result == "Temperate-Dry"
        
        # Test continental
        result = self.service._simple_classify(8.0, 600.0)
        assert result == "Continental"
        
        # Test polar
        result = self.service._simple_classify(2.0, 400.0)
        assert result == "Polar"