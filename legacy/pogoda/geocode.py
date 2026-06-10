from __future__ import annotations
from geopy.geocoders import Nominatim
from dataclasses import dataclass

@dataclass
class Location:
    name: str
    latitude: float
    longitude: float

_geolocator = None

def geocode_city(city: str, user_agent: str = "pogoda-app") -> Location:
    """Geocode a city name into coordinates using Nominatim.

    Parameters
    ----------
    city: str
        City name (can include country, e.g., "Szczecin, Poland").
    user_agent: str
        Required by Nominatim usage policy.

    Returns
    -------
    Location

    Raises
    ------
    ValueError: if no result is found.
    """
    global _geolocator
    if _geolocator is None:
        _geolocator = Nominatim(user_agent=user_agent, timeout=10)
    result = _geolocator.geocode(city)
    if not result:
        raise ValueError(f"City not found: {city}")
    return Location(name=result.address, latitude=result.latitude, longitude=result.longitude)
