from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import pickle

import numpy as np



__all__ = [
    "ClimateClassification",
    "YearlyClimateRecord",
    "ClimateAggregate",
    "ClimateResponse",
    "CompactClimateModel",
    "load_compact_climate_model",
]


# ---- Plain data containers (no Pydantic) ----
@dataclass
class ClimateClassification:
    koppen_code: str
    koppen_name: str
    trewartha_code: str
    trewartha_name: str

@dataclass
class YearlyClimateRecord:
    year: int
    avg_temp_c: float
    precipitation_mm: float
    classification: ClimateClassification

@dataclass
class ClimateAggregate:
    place: str
    start_year: int
    end_year: int
    mean_temp_c: float
    total_precip_mm: float
    dominant_classification: ClimateClassification

@dataclass
class ClimateResponse:
    place: str
    start_year: int
    end_year: int
    records: List[YearlyClimateRecord]
    aggregate: Optional[ClimateAggregate] = None

    def to_dict(self) -> Dict:
        return {
            "place": self.place,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "records": [asdict(r) for r in self.records],
            "aggregate": asdict(self.aggregate) if self.aggregate else None,
        }


class CompactClimateModel:
    """Compact climate dataset accessor.

    Expects a pickle file containing a tuple: (location_map, np_array)
      - location_map: Dict[(np.float32(lat), np.float32(lon))] -> start index in array
      - np_array layout per location:
            [year_count, year_1, 12 temp values (scaled *100), 12 precip values (scaled *10), year_2, ...]

    This class performs no global config access; dependency injection of file path keeps it testable.
    """

    def __init__(self, file_path: Path):
        self._file_path = Path(file_path)
        with self._file_path.open("rb") as f:
            location_map, np_climate_data = pickle.load(f)
        self._location_map = location_map  # key: (np.float32(lat), np.float32(lon))
        self._data = np_climate_data       # flat numpy array (dtype assumed numeric)

    @property
    def file_path(self) -> Path:
        return self._file_path

    def extract_data(self, lat: float, lon: float, years: List[int]) -> Tuple[Dict[int, List[float]], Dict[int, List[float]]]:
        """Return (temperature_dict, precipitation_dict) filtered by provided years.

        Temp values returned in Celsius, precipitation in mm.
        Returns dictionaries with year as key and list of 12 monthly values as value.
        """
        key = (np.float32(lat), np.float32(lon))
        if key not in self._location_map:
            raise KeyError(f"Location ({lat}, {lon}) not found in compact climate dataset")
        pointer = int(self._location_map[key])
        data = self._data
        year_count = int(data[pointer])
        pointer += 1
        temp_by_year: Dict[int, List[float]] = {}
        precip_by_year: Dict[int, List[float]] = {}
        target_years = set(years)
        for _ in range(year_count):
            year = int(data[pointer]); pointer += 1
            take = year in target_years
            if take:
                temps = [float(data[pointer + j] / 100.0) for j in range(12)]
            pointer += 12
            if take:
                precs = [float(data[pointer + j] / 10.0) for j in range(12)]
            pointer += 12
            if take:
                temp_by_year[year] = temps
                precip_by_year[year] = precs
        return temp_by_year, precip_by_year

    def find_closest_location(self, target_lat: float, target_lon: float) -> Tuple[float, float, float]:
        """Find the closest available location in the dataset to the target coordinates.
        
        Returns:
            Tuple of (closest_lat, closest_lon, distance_km)
        """
        import math
        
        def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            """Calculate the great circle distance between two points on Earth in kilometers."""
            # Convert decimal degrees to radians
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Radius of earth in kilometers
            r = 6371
            return c * r
        
        closest_key = None
        min_distance = float('inf')
        
        # Linear scan through all available locations
        for (lat, lon) in self._location_map.keys():
            distance = haversine_distance(target_lat, target_lon, float(lat), float(lon))
            if distance < min_distance:
                min_distance = distance
                closest_key = (lat, lon)
        
        if closest_key is None:
            raise ValueError("No locations found in the dataset")
        
        return float(closest_key[0]), float(closest_key[1]), min_distance


# ---- Simple module-level cache (singleton-like) ----
_cached_compact_model: Optional[CompactClimateModel] = None
_cached_path: Optional[Path] = None

def load_compact_climate_model(file_path: Path, force_reload: bool = False) -> CompactClimateModel:
    """Load (or return cached) CompactClimateModel from given path.

    Parameters:
        file_path: Path to the pickle file.
        force_reload: If True, always reload from disk.
    """
    global _cached_compact_model, _cached_path
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Compact climate file not found: {file_path}")
    if (
        _cached_compact_model is not None
        and _cached_path == file_path
        and not force_reload
    ):
        return _cached_compact_model
    _cached_compact_model = CompactClimateModel(file_path)
    _cached_path = file_path
    return _cached_compact_model


