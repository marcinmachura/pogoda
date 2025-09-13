"""Pydantic models for Climate API v1.

WHAT: Defines request/response validation & serialization schemas used by
the climate endpoints (city/year requests, classification structures,
aggregated & yearly responses, error shape).

WHY HERE: Keeps transport-layer data contracts close to the versioned API
namespace (`app.api.v1`). Separates them from internal dataclasses in
`app.climate.models` to avoid leaking internal representations over HTTP.
External APIs: None directly—these schemas are consumed by FastAPI for
validation and OpenAPI documentation generation.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ClimateRequest(BaseModel):
    """Request model for climate data endpoints."""
    city: str = Field(..., min_length=1, max_length=100, description="City name to get climate data for")
    years: List[int] = Field(..., min_length=1, max_length=50, description="List of years to retrieve data for")
    
    @validator('years')
    def validate_years(cls, v):
        if not v:
            raise ValueError('At least one year must be provided')
        
        for year in v:
            if year < 1950 or year > 2024:
                raise ValueError(f'Year {year} is out of valid range (1950-2024)')

        if len(set(v)) != len(v):
            raise ValueError('Duplicate years are not allowed')
            
        return sorted(v)

    class Config:
        schema_extra = {
            "example": {
                "city": "London",
                "years": [2020, 2021, 2022]
            }
        }


class ClimateClassificationData(BaseModel):
    """Climate classification with both Köppen and Trewartha systems."""
    koppen_code: str = Field(..., description="Köppen climate classification code (e.g., 'Cfb')")
    koppen_name: str = Field(..., description="Köppen climate classification name (e.g., 'Oceanic climate')")
    trewartha_code: str = Field(..., description="Trewartha climate classification code (e.g., 'Cfbk')")
    trewartha_name: str = Field(..., description="Trewartha climate classification name (e.g., 'Oceanic climate')")


class LocationData(BaseModel):
    """Location information from geocoding."""
    city: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    display_name: Optional[str] = None


class AggregatedClimateData(BaseModel):
    """Aggregated climate data with monthly averages."""
    avg_monthly_temps: List[float]  # 12 monthly average temperatures
    avg_monthly_precip: List[float]  # 12 monthly average precipitation
    classification: ClimateClassificationData

class AggregatedClimateResponse(BaseModel):
    """Response model for aggregated climate data."""
    location: LocationData
    start_year: int
    end_year: int
    climate_data: AggregatedClimateData
    distance_km: float

class YearlyClimateResponse(BaseModel):
    """Response model for yearly climate data breakdown."""
    location: LocationData
    start_year: int
    end_year: int
    yearly_data: dict[int, ClimateClassificationData]  # year -> classification
    distance_km: float

    class Config:
        schema_extra = {
            "example": {
                "location": {
                    "city": "London",
                    "latitude": 51.5074,
                    "longitude": -0.1278,
                    "country": "United Kingdom",
                    "display_name": "London, Greater London, England, United Kingdom"
                },
                "start_year": 2020,
                "end_year": 2022,
                "yearly_data": {
                    "2020": {
                        "koppen_code": "Cfb",
                        "koppen_name": "Oceanic",
                        "trewartha_code": "DO",
                        "trewartha_name": "Oceanic"
                    },
                    "2021": {
                        "koppen_code": "Cfb",
                        "koppen_name": "Oceanic",
                        "trewartha_code": "DO",
                        "trewartha_name": "Oceanic"
                    }
                },
                "distance_km": 4.98
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "error": "GeocodeError",
                "detail": "No geocoding results found for: InvalidCity"
            }
        }