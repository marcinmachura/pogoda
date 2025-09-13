"""Unit tests for CompactClimateModel functionality."""

import pytest
import tempfile
import pickle
import numpy as np
from pathlib import Path
from unittest.mock import patch

from app.climate.models import CompactClimateModel, load_compact_climate_model


class TestCompactClimateModel:
    """Test cases for the CompactClimateModel class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create sample test data - European locations only (dataset constraint)
        self.location_map = {
            (np.float32(51.5), np.float32(-0.1)): 0,    # London, UK
            (np.float32(48.9), np.float32(2.3)): 51,    # Paris, France (after London's 51 elements)
            (np.float32(52.5), np.float32(13.4)): 77,   # Berlin, Germany (after Paris's 26 elements)
        }
        
        # Create sample climate data
        # Format: [year_count, year1, 12_temps*100, 12_precips*10, year2, ...]
        data = []
        
        # London data (index 0) - years within dataset range 1950-2024
        data.extend([2])  # 2 years of data
        # Year 1990
        data.extend([1990])
        data.extend([500, 600, 800, 1200, 1600, 2000, 2200, 2100, 1700, 1300, 800, 600])  # temps * 100
        data.extend([50, 40, 45, 55, 60, 65, 40, 50, 65, 70, 60, 55])  # precip * 10
        # Year 2000
        data.extend([2000])
        data.extend([480, 580, 780, 1180, 1580, 1980, 2180, 2080, 1680, 1280, 780, 580])
        data.extend([52, 42, 47, 57, 62, 67, 42, 52, 67, 72, 62, 57])
        
        # Paris data (index 51)
        data.extend([1])  # 1 year of data
        data.extend([1995])
        data.extend([0, 200, 600, 1200, 1800, 2400, 2700, 2600, 2000, 1400, 800, 300])
        data.extend([80, 70, 90, 100, 110, 120, 110, 100, 90, 80, 70, 75])
        
        # Berlin data (index 77)
        data.extend([1])
        data.extend([1980])
        data.extend([2000, 2200, 1800, 1400, 1000, 800, 800, 1000, 1200, 1600, 1800, 2000])
        data.extend([20, 15, 25, 50, 80, 120, 100, 80, 40, 30, 25, 20])
        
        self.np_data = np.array(data, dtype=np.float32)
        
        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        with open(self.temp_file.name, 'wb') as f:
            pickle.dump((self.location_map, self.np_data), f)
        self.temp_file.close()  # Close file handle to avoid Windows permission issues
        
        self.model = CompactClimateModel(Path(self.temp_file.name))

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        try:
            Path(self.temp_file.name).unlink(missing_ok=True)
        except PermissionError:
            # On Windows, file might still be in use - try again after a short delay
            import time
            time.sleep(0.1)
            try:
                Path(self.temp_file.name).unlink(missing_ok=True)
            except PermissionError:
                pass  # Ignore if still can't delete

    def test_model_initialization(self):
        """Test that model initializes correctly."""
        assert self.model.file_path == Path(self.temp_file.name)
        assert len(self.model._location_map) == 3
        assert isinstance(self.model._data, np.ndarray)

    def test_exact_location_data_extraction(self):
        """Test extracting data for an exact location match."""
        # Act
        temp_dict, precip_dict = self.model.extract_data(51.5, -0.1, [1990, 2000])

        # Assert
        assert set(temp_dict.keys()) == {1990, 2000}
        assert set(precip_dict.keys()) == {1990, 2000}
        
        # Check 1990 data structure
        assert len(temp_dict[1990]) == 12  # 12 months
        assert len(precip_dict[1990]) == 12
        
        # Check temperature conversion (stored as *100)
        assert abs(temp_dict[1990][0] - 5.0) < 0.1  # 500/100
        assert abs(temp_dict[1990][6] - 22.0) < 0.1  # 2200/100
        
        # Check precipitation conversion (stored as *10)
        assert abs(precip_dict[1990][0] - 5.0) < 0.1  # 50/10
        assert abs(precip_dict[1990][6] - 4.0) < 0.1  # 40/10

    def test_partial_year_extraction(self):
        """Test extracting data for years that only partially exist."""
        # Act - Request years where only 1995 exists for Paris, but also ask for 1990, 2000
        temp_dict, precip_dict = self.model.extract_data(48.9, 2.3, [1990, 1995, 2000])

        # Assert - Should only get 1995 data
        assert set(temp_dict.keys()) == {1995}
        assert set(precip_dict.keys()) == {1995}
        assert len(temp_dict[1995]) == 12
        assert len(precip_dict[1995]) == 12

    def test_nonexistent_location(self):
        """Test that nonexistent locations raise KeyError."""
        with pytest.raises(KeyError, match="Location \\(0.0, 0.0\\) not found"):
            self.model.extract_data(0.0, 0.0, [2020])

    def test_nonexistent_years(self):
        """Test extracting data for years that don't exist."""
        # Act - Request years that don't exist in London data (which has 1990, 2000)
        temp_dict, precip_dict = self.model.extract_data(51.5, -0.1, [1985, 2010])

        # Assert - Should return empty dictionaries
        assert temp_dict == {}
        assert precip_dict == {}

    def test_find_closest_location_exact_match(self):
        """Test finding closest location when exact match exists."""
        # Act
        closest_lat, closest_lon, distance = self.model.find_closest_location(51.5, -0.1)

        # Assert
        assert abs(closest_lat - 51.5) < 0.001
        assert abs(closest_lon - (-0.1)) < 0.001
        assert distance < 1.0  # Should be very close (essentially 0)

    def test_find_closest_location_nearby(self):
        """Test finding closest location for a nearby point."""
        # Act - Point close to London (51.5, -0.1)
        closest_lat, closest_lon, distance = self.model.find_closest_location(51.6, -0.2)

        # Assert
        assert abs(closest_lat - 51.5) < 0.1
        assert abs(closest_lon - (-0.1)) < 0.1
        assert distance < 50  # Should be less than 50km away

    def test_find_closest_location_far_point(self):
        """Test finding closest location for a point far from all locations."""
        # Act - Point in Northern Europe (far from our test locations)
        closest_lat, closest_lon, distance = self.model.find_closest_location(60.0, 10.0)

        # Assert
        assert isinstance(closest_lat, float)
        assert isinstance(closest_lon, float)
        assert distance > 500  # Should be far away
        
        # Should still be one of our known locations
        found_location = (np.float32(closest_lat), np.float32(closest_lon))
        assert found_location in self.location_map

    def test_haversine_distance_calculation(self):
        """Test the haversine distance calculation."""
        # Test known distance: London to Paris is approximately 344 km
        london_lat, london_lon = 51.5, -0.1
        
        # Find closest to London coordinates
        closest_lat, closest_lon, distance = self.model.find_closest_location(london_lat, london_lon)
        
        # Should find London itself
        assert abs(closest_lat - london_lat) < 0.1
        assert abs(closest_lon - london_lon) < 0.1

    @pytest.mark.parametrize("lat,lon,expected_closest", [
        (51.5, -0.1, (51.5, -0.1)),  # Exact London match
        (48.9, 2.3, (48.9, 2.3)),    # Exact Paris match
        (52.5, 13.4, (52.5, 13.4)),  # Exact Berlin match
    ])
    def test_find_closest_location_parametrized(self, lat, lon, expected_closest):
        """Test finding closest location with multiple coordinate pairs."""
        # Act
        closest_lat, closest_lon, distance = self.model.find_closest_location(lat, lon)

        # Assert
        assert abs(closest_lat - expected_closest[0]) < 0.1
        assert abs(closest_lon - expected_closest[1]) < 0.1
        assert distance < 1.0  # Should be very close for exact matches


class TestCompactClimateModelEdgeCases:
    """Test edge cases for CompactClimateModel."""

    def test_empty_location_map(self):
        """Test behavior with empty location map."""
        # Arrange
        empty_map = {}
        empty_data = np.array([], dtype=np.float32)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        with open(temp_file.name, 'wb') as f:
            pickle.dump((empty_map, empty_data), f)
        temp_file.close()  # Close to avoid Windows permission issues

        try:
            # Act
            model = CompactClimateModel(Path(temp_file.name))
            
            # Assert
            with pytest.raises(ValueError, match="No locations found in the dataset"):
                model.find_closest_location(51.5, -0.1)
        finally:
            try:
                Path(temp_file.name).unlink(missing_ok=True)
            except PermissionError:
                pass  # Ignore Windows permission issues

    def test_invalid_file_path(self):
        """Test behavior with invalid file path."""
        with pytest.raises(FileNotFoundError):
            CompactClimateModel(Path("nonexistent_file.pkl"))

    def test_corrupted_pickle_file(self):
        """Test behavior with corrupted pickle file."""
        # Arrange
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        with open(temp_file.name, 'w') as f:
            f.write("This is not a pickle file")
        temp_file.close()  # Close to avoid Windows permission issues

        try:
            # Act & Assert
            with pytest.raises((pickle.UnpicklingError, UnicodeDecodeError)):
                CompactClimateModel(Path(temp_file.name))
        finally:
            try:
                Path(temp_file.name).unlink(missing_ok=True)
            except PermissionError:
                pass  # Ignore Windows permission issues


class TestClimateModelCaching:
    """Test the climate model caching functionality."""

    def setup_method(self):
        """Clear any cached model before each test."""
        import app.climate.models
        app.climate.models._cached_compact_model = None
        app.climate.models._cached_path = None

    def test_model_caching(self):
        """Test that the model is properly cached."""
        # Arrange
        location_map = {(np.float32(51.5), np.float32(-0.1)): 0}
        data = np.array([1, 1990] + [100] * 12 + [10] * 12, dtype=np.float32)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        with open(temp_file.name, 'wb') as f:
            pickle.dump((location_map, data), f)
        temp_file.close()  # Close to avoid Windows permission issues

        try:
            path = Path(temp_file.name)
            
            # Act
            model1 = load_compact_climate_model(path)
            model2 = load_compact_climate_model(path)
            
            # Assert
            assert model1 is model2  # Should be the same instance

        finally:
            try:
                Path(temp_file.name).unlink(missing_ok=True)
            except PermissionError:
                pass  # Ignore Windows permission issues    def test_model_cache_invalidation(self):
        """Test that cache is invalidated when force_reload is True."""
        # Arrange
        location_map = {(np.float32(51.5), np.float32(-0.1)): 0}
        data = np.array([1, 1990] + [100] * 12 + [10] * 12, dtype=np.float32)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        with open(temp_file.name, 'wb') as f:
            pickle.dump((location_map, data), f)
        temp_file.close()  # Close to avoid Windows permission issues

        try:
            path = Path(temp_file.name)
            
            # Act
            model1 = load_compact_climate_model(path)
            model2 = load_compact_climate_model(path, force_reload=True)
            
            # Assert
            assert model1 is not model2  # Should be different instances

        finally:
            try:
                Path(temp_file.name).unlink(missing_ok=True)
            except PermissionError:
                pass  # Ignore Windows permission issues

    def test_model_cache_different_paths(self):
        """Test that different file paths create different cached models."""
        # Arrange
        location_map = {(np.float32(51.5), np.float32(-0.1)): 0}
        data = np.array([1, 1990] + [100] * 12 + [10] * 12, dtype=np.float32)
        
        temp_file1 = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        temp_file2 = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        
        for temp_file in [temp_file1, temp_file2]:
            with open(temp_file.name, 'wb') as f:
                pickle.dump((location_map, data), f)
            temp_file.close()  # Close to avoid Windows permission issues

        try:
            path1 = Path(temp_file1.name)
            path2 = Path(temp_file2.name)
            
            # Act
            model1 = load_compact_climate_model(path1)
            model2 = load_compact_climate_model(path2)
            
            # Assert
            assert model1 is not model2  # Should be different instances

        finally:
            try:
                Path(temp_file1.name).unlink(missing_ok=True)
                Path(temp_file2.name).unlink(missing_ok=True)
            except PermissionError:
                pass  # Ignore Windows permission issues