from typing import *
import json
import numpy as np
import pickle
def encode_coordinates(lat: float, lon: float) -> int:
    """
    Encodes latitude and longitude into a single 64-bit integer.
    
    Human readable format: [sign][lat_digits][sign][lon_digits]
    lat: -90.00000 to +90.00000 -> [0/1][9000000] (1 + 7 digits = 8 digits)
    lon: -180.00000 to +180.00000 -> [0/1][18000000] (1 + 8 digits = 9 digits)
    Total: 17 digits, fits comfortably in int64 (max ~19 digits)
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
    
    Returns:
        int: The encoded 64-bit integer.
    """
    lat_sign = 0 if lat >= 0.0 else 1
    lon_sign = 0 if lon >= 0.0 else 1
    
    lat_abs = int(abs(lat) * 100000.0)
    lon_abs = int(abs(lon) * 100000.0)
    
    # Format: [lat_sign][lat_7digits][lon_sign][lon_8digits]
    # Example: lat=52.12345, lon=-21.67890 -> 05212345102167890 (Note: The original example has a slight error in the lon part. 
    # The lon sign is 1, and the value is 21.67890, which becomes 02167890. The final result should be 05212345102167890)
    encoded = (lat_sign * 100000000000000000) + \
              (lat_abs * 1000000000) + \
              (lon_sign * 100000000) + \
              lon_abs
    
    return encoded

def decode_coordinates(encoded: int) -> Tuple[np.float32,np.float32]:
    """
    Decodes a 64-bit integer back into latitude and longitude.
    
    Args:
        encoded (int): The encoded 64-bit integer.
    
    Returns:
        tuple[float, float]: A tuple containing the decoded latitude and longitude.
    """
    lon_abs = encoded % 100000000
    lon_sign = (encoded // 100000000) % 10
    lat_abs = (encoded // 1000000000) % 10000000
    lat_sign = encoded // 100000000000000000

    lat = np.float32(lat_abs) / 100000.0 if lat_sign == 0 else -(np.float32(lat_abs) / 100000.0)
    lon = np.float32(lon_abs) / 100000.0 if lon_sign == 0 else -(np.float32(lon_abs) / 100000.0)

    return (lat, lon)


# Top 10 European cities with their coordinates
top_european_cities = [
    {"name": "London", "country": "United Kingdom", "lat": 51.5074, "lon": -0.1278},
    {"name": "Berlin", "country": "Germany", "lat": 52.5200, "lon": 13.4050},
    {"name": "Madrid", "country": "Spain", "lat": 40.4168, "lon": -3.7038},
    {"name": "Rome", "country": "Italy", "lat": 41.9028, "lon": 12.4964},
    {"name": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522},
    {"name": "Bucharest", "country": "Romania", "lat": 44.4268, "lon": 26.1025},
    {"name": "Vienna", "country": "Austria", "lat": 48.2082, "lon": 16.3738},
    {"name": "Hamburg", "country": "Germany", "lat": 53.5511, "lon": 9.9937},
    {"name": "Warsaw", "country": "Poland", "lat": 52.2297, "lon": 21.0122},
    {"name": "Barcelona", "country": "Spain", "lat": 41.3851, "lon": 2.1734}
]

test_data = True
print("Converting JSON to PKL model file.")
print("test mode =", test_data)
output_file = "climate_test.pkl" if test_data else "climate_compact.pkl"
location_map  = {}
climate_data : list[np.int16] = []
cursor = 0
with open("../data/models/climate_optimized.json") as f:
    for line in f:
        row = json.loads(line)
        lat, lon = decode_coordinates(row["Coordinate"])
        
        # If test_data is True, skip points that are too far from European cities
        if test_data:
            skip_point = True
            for city in top_european_cities:
                # Check if point is within 0.1 degrees of any European city
                if abs(lat - city["lat"]) <= 0.1 and abs(lon - city["lon"]) <= 0.1:
                    skip_point = False
                    break
            if skip_point:
                continue

        location_map[(lat,lon)] = len(climate_data)
        climate_data.append(np.int16(len(row["ClimateData"])))
        for year in row["ClimateData"].keys():
            climate_data.append(np.int16(year))
            row["ClimateData"][year]
            climate_data.extend(np.int16(x) for x in row["ClimateData"][year]["Temperatures"])
            climate_data.extend(np.int16(x) for x in row["ClimateData"][year]["Precipitation"])   

np_climate_data = np.array(climate_data)
print("Locations:", len(location_map))
print("Datapoints:", len(np_climate_data))
with open("../data/models/"+output_file, "wb") as f:
    pickle.dump((location_map,np_climate_data), f)

