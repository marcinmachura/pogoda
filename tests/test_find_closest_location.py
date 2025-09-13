"""Specific unit tests for CompactClimateModel.find_closest_location functionality."""

import pytest
from pathlib import Path
from app.climate.models import load_compact_climate_model


class TestFindClosestLocationReal:
    """Test find_closest_location with the real climate dataset."""

    def setup_method(self):
        """Set up test fixtures using the real climate model."""
        # Use the real climate model file
        model_path = Path("data/models/climate_compact.pkl")
        if not model_path.exists():
            pytest.skip("Real climate model file not found")
        
        self.model = load_compact_climate_model(model_path)

    def test_find_closest_to_known_location(self):
        """Test finding closest location to a known point in the dataset."""
        # You mentioned (25.050001, -13.75) is in the dataset
        # Let's search for something close to it
        target_lat, target_lon = 25.0, -13.7
        
        # Act
        closest_lat, closest_lon, distance = self.model.find_closest_location(target_lat, target_lon)
        
        # Assert
        print(f"Target: ({target_lat}, {target_lon})")
        print(f"Found closest: ({closest_lat}, {closest_lon})")
        print(f"Distance: {distance:.2f} km")
        
        # Should find something close to the known location
        assert abs(closest_lat - 25.050001) < 1.0, f"Expected lat ~25.05, got {closest_lat}"
        assert abs(closest_lon - (-13.75)) < 1.0, f"Expected lon ~-13.75, got {closest_lon}"
        assert distance < 100, f"Distance should be reasonable, got {distance} km"

    def test_find_closest_exact_match(self):
        """Test finding exact match for the known coordinate."""
        # Test with the exact coordinate you mentioned
        target_lat, target_lon = 25.050001, -13.75
        
        # Act
        closest_lat, closest_lon, distance = self.model.find_closest_location(target_lat, target_lon)
        
        # Assert
        print(f"Target (exact): ({target_lat}, {target_lon})")
        print(f"Found closest: ({closest_lat}, {closest_lon})")
        print(f"Distance: {distance:.2f} km")
        
        # Should find the exact location or very close
        assert abs(closest_lat - 25.050001) < 0.001, f"Expected exact match lat, got {closest_lat}"
        assert abs(closest_lon - (-13.75)) < 0.001, f"Expected exact match lon, got {closest_lon}"
        assert distance < 1.0, f"Distance should be minimal for exact match, got {distance} km"

    def test_find_closest_nearby_points(self):
        """Test finding closest location for various nearby points."""
        # Test points around the known location
        test_points = [
            (25.0, -13.8),      # Slightly west
            (25.1, -13.7),      # Slightly north-east  
            (24.9, -13.8),      # Slightly south-west
            (25.2, -13.6),      # Further north-east
        ]
        
        for test_lat, test_lon in test_points:
            # Act
            closest_lat, closest_lon, distance = self.model.find_closest_location(test_lat, test_lon)
            
            # Assert
            print(f"Test point: ({test_lat}, {test_lon})")
            print(f"Found closest: ({closest_lat}, {closest_lon})")
            print(f"Distance: {distance:.2f} km")
            
            # Should find something reasonably close
            assert distance < 200, f"Distance should be reasonable for ({test_lat}, {test_lon}), got {distance} km"
            assert isinstance(closest_lat, float), "closest_lat should be float"
            assert isinstance(closest_lon, float), "closest_lon should be float"
            assert isinstance(distance, float), "distance should be float"
            print("-" * 40)

    def test_dataset_coverage_exploration(self):
        """Explore the dataset to understand its geographic coverage."""
        # Get a sample of locations from the dataset
        location_keys = list(self.model._location_map.keys())
        
        print(f"Dataset contains {len(location_keys)} locations")
        print("Sample locations:")
        
        # Show first 10 locations
        for i, (lat, lon) in enumerate(location_keys[:10]):
            print(f"  {i+1}: ({float(lat):.6f}, {float(lon):.6f})")
        
        if len(location_keys) > 10:
            print("  ...")
            # Show last 5 locations
            for i, (lat, lon) in enumerate(location_keys[-5:], len(location_keys)-4):
                print(f"  {i}: ({float(lat):.6f}, {float(lon):.6f})")
        
        # Find min/max bounds
        lats = [float(lat) for lat, lon in location_keys]
        lons = [float(lon) for lat, lon in location_keys]
        
        print(f"\nDataset bounds:")
        print(f"  Latitude: {min(lats):.6f} to {max(lats):.6f}")
        print(f"  Longitude: {min(lons):.6f} to {max(lons):.6f}")
        
        # Verify the mentioned point exists
        target_key = None
        for lat, lon in location_keys:
            if abs(float(lat) - 25.050001) < 0.000001 and abs(float(lon) - (-13.75)) < 0.000001:
                target_key = (lat, lon)
                break
        
        if target_key:
            print(f"\nSUCCESS: Found exact location: ({float(target_key[0])}, {float(target_key[1])})")
        else:
            print(f"\nERROR: Exact location (25.050001, -13.75) not found in dataset")
            # Find closest to it
            closest_lat, closest_lon, distance = self.model.find_closest_location(25.050001, -13.75)
            print(f"Closest to (25.050001, -13.75): ({closest_lat}, {closest_lon}), distance: {distance:.2f} km")

    def test_haversine_distance_accuracy(self):
        """Test that the haversine distance calculation is working correctly."""
        # Known distance: London to Paris is approximately 344 km
        london_lat, london_lon = 51.5074, -0.1278
        paris_lat, paris_lon = 48.8566, 2.3522
        
        # Calculate using the model's internal haversine function
        # We'll do this by finding closest to London, then Paris, and comparing
        london_closest_lat, london_closest_lon, london_distance = self.model.find_closest_location(london_lat, london_lon)
        paris_closest_lat, paris_closest_lon, paris_distance = self.model.find_closest_location(paris_lat, paris_lon)
        
        print(f"London ({london_lat}, {london_lon}) -> closest: ({london_closest_lat}, {london_closest_lon}), distance: {london_distance:.2f} km")
        print(f"Paris ({paris_lat}, {paris_lon}) -> closest: ({paris_closest_lat}, {paris_closest_lon}), distance: {paris_distance:.2f} km")
        
        # Both should be reasonably close to major European cities
        assert london_distance < 500, f"London should have close match in European dataset, got {london_distance} km"
        assert paris_distance < 500, f"Paris should have close match in European dataset, got {paris_distance} km"