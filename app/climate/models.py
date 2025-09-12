from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pickle

import numpy as np
import pandas as pd

__all__ = [
    "CompactClimateModel",
    "load_compact_climate_model",
]


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

    def extract_data(self, lat: float, lon: float, years: List[int]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Return (temperature_df, precipitation_df) filtered by provided years.

        Temp values returned in Celsius, precipitation in mm.
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

        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        df_temp = pd.DataFrame.from_dict(temp_by_year, orient="index", columns=month_names)
        df_precip = pd.DataFrame.from_dict(precip_by_year, orient="index", columns=month_names)
        return df_temp, df_precip


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


