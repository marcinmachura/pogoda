"""Geocoding utilities using OpenStreetMap Nominatim.

WHAT: Provides `GeocodingService` to translate city names to coordinates
with minimal fields captured in `GeoLocation` dataclass. Wraps HTTP calls
and normalizes error handling via `GeocodeError`.

WHY HERE: Lives in climate domain package because geocoding is prerequisite
for climate model lookup; isolates external API specifics (Nominatim
endpoint, headers, timeouts) from higher-level service logic.
External dependency: OpenStreetMap Nominatim public API.
"""

from __future__ import annotations
import requests
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class GeoLocation:
    city: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    display_name: Optional[str] = None


class GeocodeError(Exception):
    pass


class GeocodingService:
    """Simple geocoding service using OpenStreetMap Nominatim API."""
    
    def __init__(self, base_url: str = "https://nominatim.openstreetmap.org"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ClimateAPI/1.0 (educational/research use)'
        })
    
    def geocode(self, city_name: str) -> GeoLocation:
        """Convert city name to latitude/longitude coordinates.
        
        Args:
            city_name: Name of the city to geocode
            
        Returns:
            GeoLocation with coordinates
            
        Raises:
            GeocodeError: If geocoding fails or no results found
        """
        try:
            response = self.session.get(
                f"{self.base_url}/search",
                params={
                    'q': city_name,
                    'format': 'json',
                    'limit': 1,
                    'addressdetails': 1
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if not data:
                raise GeocodeError(f"No geocoding results found for: {city_name}")
                
            result = data[0]
            return GeoLocation(
                city=city_name,
                latitude=float(result['lat']),
                longitude=float(result['lon']),
                country=result.get('address', {}).get('country'),
                display_name=result.get('display_name')
            )
            
        except requests.RequestException as e:
            raise GeocodeError(f"Geocoding request failed: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise GeocodeError(f"Failed to parse geocoding response: {e}")