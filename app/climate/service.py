from __future__ import annotations

from typing import List, Optional, Tuple
from pathlib import Path

from .models import YearlyClimateRecord, ClimateClassification, load_compact_climate_model
from .geocode import GeocodingService, GeoLocation, GeocodeError
from .classifiers import classify_koppen, classify_trewartha, ClassificationError
from ..core.config import get_settings


class ClimateService:
    """Climate service that integrates geocoding, real climate data, and climate classification."""

    def __init__(self):
        self.geocoding_service = GeocodingService()
        self.settings = get_settings()

    def get_aggregated_climate_data(
        self, 
        city: str, 
        years: List[int]
    ) -> tuple[GeoLocation, List[float], List[float], ClimateClassification, float]:
        """Get aggregated climate data for a city across multiple years.
        
        Returns monthly averages across all years and single classification.
        
        Returns:
            Tuple of (location, avg_monthly_temps, avg_monthly_precip, classification, distance_km)
        """
        # Step 1: Geocode the city
        try:
            location = self.geocoding_service.geocode(city)
        except GeocodeError:
            raise ValueError(f"Could not find location for city: {city}")

        # Step 2: Get raw monthly data from compact climate model
        try:
            monthly_data, distance_km = self._get_monthly_data_from_compact_model(location, years)
        except (FileNotFoundError, KeyError) as e:
            raise ValueError(f"Could not retrieve climate data for {city}: {e}")

        # Step 3: Calculate monthly averages across all years
        avg_monthly_temps = []
        avg_monthly_precip = []
        
        for month in range(12):
            month_temps = [monthly_data[year]['temps'][month] for year in years if year in monthly_data]
            month_precips = [monthly_data[year]['precips'][month] for year in years if year in monthly_data]
            
            avg_monthly_temps.append(sum(month_temps) / len(month_temps) if month_temps else 0.0)
            avg_monthly_precip.append(sum(month_precips) / len(month_precips) if month_precips else 0.0)

        # Step 4: Apply classification to averaged monthly data
        classification = self._classify_climate(avg_monthly_temps, avg_monthly_precip, location.latitude)

        return location, avg_monthly_temps, avg_monthly_precip, classification, distance_km

    def get_yearly_climate_data(
        self, 
        city: str, 
        years: List[int]
    ) -> tuple[GeoLocation, dict[int, ClimateClassification], float]:
        """Get yearly breakdown of climate classifications.
        
        Returns:
            Tuple of (location, year_classifications, distance_km)
        """
        # Step 1: Geocode the city
        try:
            location = self.geocoding_service.geocode(city)
        except GeocodeError:
            raise ValueError(f"Could not find location for city: {city}")

        # Step 2: Get raw monthly data from compact climate model
        try:
            monthly_data, distance_km = self._get_monthly_data_from_compact_model(location, years)
        except (FileNotFoundError, KeyError) as e:
            raise ValueError(f"Could not retrieve climate data for {city}: {e}")

        # Step 3: Apply classification to each year individually
        year_classifications = {}
        for year in years:
            if year in monthly_data:
                temps = monthly_data[year]['temps']
                precips = monthly_data[year]['precips']
                classification = self._classify_climate(temps, precips, location.latitude)
                year_classifications[year] = classification

        return location, year_classifications, distance_km

    def _get_monthly_data_from_compact_model(
        self, 
        location: GeoLocation, 
        years: List[int]
    ) -> Tuple[dict[int, dict[str, List[float]]], float]:
        """Get raw monthly temperature and precipitation data from the compact climate model.
        
        Returns:
            Tuple of (monthly_data, distance_km) where monthly_data has structure:
            {year: {'temps': [12 monthly temps], 'precips': [12 monthly precips]}}
        """
        model_path = self.settings.active_model_path
        if not model_path.exists():
            # Try the compact model file that exists
            compact_path = Path("data/models/climate_compact.pkl")
            if compact_path.exists():
                model_path = compact_path
            else:
                raise FileNotFoundError(f"No climate model found")

        climate_model = load_compact_climate_model(model_path)
        
        # Find the closest available location in the dataset
        closest_lat, closest_lon, distance_km = climate_model.find_closest_location(
            location.latitude, 
            location.longitude
        )
        
        # Extract climate data using the closest location
        temp_dict, precip_dict = climate_model.extract_data(
            closest_lat, 
            closest_lon, 
            years
        )
        
        # Restructure data for easier monthly access
        monthly_data = {}
        for year in years:
            if year in temp_dict and year in precip_dict:
                monthly_data[year] = {
                    'temps': temp_dict[year],
                    'precips': precip_dict[year]
                }
        
        return monthly_data, distance_km

    def _get_data_from_compact_model(
        self, 
        location: GeoLocation, 
        years: List[int]
    ) -> Tuple[List[YearlyClimateRecord], float]:
        """Get climate data from the compact climate model.
        
        Returns:
            Tuple of (records, distance_km) where distance_km is the distance
            between the requested location and the actual climate station.
        """
        model_path = self.settings.active_model_path
        if not model_path.exists():
            # Try the compact model file that exists
            compact_path = Path("data/models/climate_compact.pkl")
            if compact_path.exists():
                model_path = compact_path
            else:
                raise FileNotFoundError(f"No climate model found")

        climate_model = load_compact_climate_model(model_path)
        
        # Find the closest available location in the dataset
        closest_lat, closest_lon, distance_km = climate_model.find_closest_location(
            location.latitude, 
            location.longitude
        )
        
        # Extract climate data using the closest location
        temp_dict, precip_dict = climate_model.extract_data(
            closest_lat, 
            closest_lon, 
            years
        )
        
        records = []
        for year in years:
            if year in temp_dict and year in precip_dict:
                temps = temp_dict[year]
                precips = precip_dict[year]
                
                # Calculate yearly averages
                avg_temp = sum(temps) / len(temps)
                total_precip = sum(precips)
                
                # Apply climate classification
                classification = self._classify_climate(temps, precips, location.latitude)
                
                record = YearlyClimateRecord(
                    year=year,
                    avg_temp_c=round(avg_temp, 2),
                    precipitation_mm=round(total_precip, 1),
                    classification=classification
                )
                records.append(record)
        
        return records, distance_km


    def _classify_climate(self, temps: List[float], precips: List[float], latitude: float) -> ClimateClassification:
        """Apply climate classification with fallbacks."""
        
        # Try Köppen classification
        koppen_code = "Unknown"
        koppen_name = "Unknown"
        try:
            koppen_code, koppen_details = classify_koppen(temps, precips, latitude)
            koppen_name = self._get_koppen_name(koppen_code)
        except ClassificationError as e:
            # Fall back to simple classification for Köppen
            avg_temp = sum(temps) / len(temps)
            total_precip = sum(precips)
            koppen_code = self._simple_classify(avg_temp, total_precip)
            koppen_name = koppen_code
        except Exception as e:
            # Fall back to simple classification for Köppen
            avg_temp = sum(temps) / len(temps)
            total_precip = sum(precips)
            koppen_code = self._simple_classify(avg_temp, total_precip)
            koppen_name = koppen_code
        
        # Try Trewartha classification
        trewartha_code = "Unknown"
        trewartha_name = "Unknown"
        try:
            trewartha_code, trewartha_details = classify_trewartha(temps, precips, latitude)
            trewartha_name = self._get_trewartha_name(trewartha_code)
        except ClassificationError as e:
            # Fall back to simple classification for Trewartha
            avg_temp = sum(temps) / len(temps)
            total_precip = sum(precips)
            trewartha_code = self._simple_classify(avg_temp, total_precip)
            trewartha_name = trewartha_code
        except Exception as e:
            # Fall back to simple classification for Trewartha
            avg_temp = sum(temps) / len(temps)
            total_precip = sum(precips)
            trewartha_code = self._simple_classify(avg_temp, total_precip)
            trewartha_name = trewartha_code
            total_precip = sum(precips)
            trewartha_code = self._simple_classify(avg_temp, total_precip)
            trewartha_name = trewartha_code
        
        return ClimateClassification(
            koppen_code=koppen_code,
            koppen_name=koppen_name,
            trewartha_code=trewartha_code,
            trewartha_name=trewartha_name
        )

    def _get_koppen_name(self, code: str) -> str:
        """Get Köppen climate name from code."""
        koppen_names = {
            "Af": "Tropical rainforest",
            "Am": "Tropical monsoon", 
            "Aw": "Tropical savanna",
            "BWh": "Hot desert",
            "BWk": "Cold desert",
            "BSh": "Hot semi-arid",
            "BSk": "Cold semi-arid",
            "Cfa": "Humid subtropical",
            "Cfb": "Oceanic",
            "Cfc": "Subpolar oceanic",
            "Csa": "Mediterranean hot-summer",
            "Csb": "Mediterranean warm-summer",
            "Csc": "Mediterranean cold-summer",
            "Cwa": "Humid subtropical (dry winter)",
            "Cwb": "Subtropical highland",
            "Cwc": "Cold subtropical highland",
            "Dfa": "Hot-summer humid continental",
            "Dfb": "Warm-summer humid continental",
            "Dfc": "Subarctic",
            "Dfd": "Extremely cold subarctic",
            "ET": "Tundra",
            "EF": "Ice cap"
        }
        return koppen_names.get(code, code)

    def _get_trewartha_name(self, code: str) -> str:
        """Get Trewartha climate name from code."""
        trewartha_names = {
            "Ar": "Tropical wet",
            "Aw": "Tropical wet-dry",
            "BWh": "Hot desert",
            "BWk": "Cold desert", 
            "BSh": "Hot steppe",
            "BSk": "Cold steppe",
            "Cf": "Subtropical",
            "Cs": "Mediterranean",
            "Do": "Oceanic",
            "Dc": "Continental",
            "E": "Boreal",
            "Ft": "Tundra",
            "Fi": "Ice cap"
        }
        # Try to match the first few characters
        for key in trewartha_names:
            if code.startswith(key):
                return trewartha_names[key]
        return code

    def _simple_classify(self, avg_temp: float, total_precip: float) -> str:
        """Simple climate classification fallback."""
        if avg_temp >= 25:
            return "Tropical"
        elif avg_temp >= 15:
            if total_precip > 1000:
                return "Temperate-Wet"
            else:
                return "Temperate-Dry"
        elif avg_temp >= 5:
            return "Continental"
        else:
            return "Polar"