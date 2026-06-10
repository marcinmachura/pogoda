#!/usr/bin/env python3
"""
Script to convert parquet files to JSON format with coordinate encoding and data transformations.
Processes both temperature (tg) and precipitation (rr) data.
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from typing import Tuple, Dict, Any

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
    encoded = (lat_sign * 100000000000000000) + \
              (lat_abs * 1000000000) + \
              (lon_sign * 100000000) + \
              lon_abs
    
    return encoded

def decode_coordinates(encoded: int) -> Tuple[np.float32, np.float32]:
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

def load_parquet_file(file_path: str) -> pd.DataFrame:
    """
    Load a single parquet file.
    
    Args:
        file_path (str): Path to parquet file
    
    Returns:
        pd.DataFrame: Loaded DataFrame
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    df = pd.read_parquet(file_path)
    print(f"Loaded data from: {file_path}")
    print(f"  Shape: {df.shape}")
    
    return df

def transform_data(df: pd.DataFrame, data_type: str) -> pd.DataFrame:
    """
    Transform the data according to specifications.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        data_type (str): 'temperature' or 'precipitation'
    
    Returns:
        pd.DataFrame: Transformed DataFrame
    """
    df = df.copy()
    
    # Extract year and month
    df['year'] = df['time'].dt.year
    df['month'] = df['time'].dt.month
    
    # Encode coordinates
    df['encoded_coord'] = df.apply(lambda row: encode_coordinates(row['latitude'], row['longitude']), axis=1)
    
    # Transform the data values
    if data_type == 'temperature':
        # Convert temperature to int16 by multiplying by 100
        df['value_int'] = (df['tg'] * 100).round().astype(np.int16)
    elif data_type == 'precipitation':
        # Convert precipitation to int16 by multiplying by 10
        df['value_int'] = (df['rr'] * 10).round().astype(np.int16)
    
    return df[['encoded_coord', 'year', 'month', 'value_int']]

def create_temperature_dictionary(temp_df: pd.DataFrame) -> Dict[int, Dict[int, list]]:
    """
    Create initial climate data dictionary from temperature data.
    
    Args:
        temp_df (pd.DataFrame): Transformed temperature data
    
    Returns:
        Dict: Coordinates -> {Year -> [temp_list]}
    """
    climate_data = {}
    
    print("Processing temperature data...")
    # Group temperature data by coordinate and year
    temp_grouped = temp_df.groupby(['encoded_coord', 'year'])
    
    for (coord, year), group in temp_grouped:
        if coord not in climate_data:
            climate_data[coord] = {}
        
        # Sort by month and get temperature values
        monthly_temps = group.sort_values('month')['value_int'].tolist()
        
        # Only keep if we have all 12 months
        if len(monthly_temps) == 12:
            climate_data[coord][year] = monthly_temps
    
    return climate_data

def update_with_precipitation(climate_data: Dict[int, Dict[int, list]], precip_df: pd.DataFrame) -> Dict[int, Dict[int, Tuple[list, list]]]:
    """
    Update climate dictionary with precipitation data.
    
    Args:
        climate_data: Existing temperature dictionary
        precip_df: Transformed precipitation data
    
    Returns:
        Dict: Updated coordinates -> {Year -> ([temp_list], [precip_list])}
    """
    updated_data = {}
    
    print("Processing precipitation data...")
    # Group precipitation data by coordinate and year
    precip_grouped = precip_df.groupby(['encoded_coord', 'year'])
    
    # Convert temperature data to new format and prepare for precipitation
    for coord in climate_data:
        updated_data[coord] = {}
        for year, temp_list in climate_data[coord].items():
            updated_data[coord][year] = (temp_list, [])
    
    # Add precipitation data
    for (coord, year), group in precip_grouped:
        if coord not in updated_data:
            continue  # Skip if no temperature data for this coordinate
        if year not in updated_data[coord]:
            continue  # Skip if no temperature data for this year
        
        # Sort by month and get precipitation values
        monthly_precip = group.sort_values('month')['value_int'].tolist()
        
        # Only keep if we have all 12 months
        if len(monthly_precip) == 12:
            temp_list = updated_data[coord][year][0]
            updated_data[coord][year] = (temp_list, monthly_precip)
        else:
            # Remove incomplete year
            if year in updated_data[coord]:
                del updated_data[coord][year]
    
    return updated_data

def filter_complete_records(climate_data: Dict[int, Dict[int, Tuple[list, list]]]) -> Dict[int, Dict[int, Tuple[list, list]]]:
    """
    Filter out incomplete records (missing temperature or precipitation data).
    
    Args:
        climate_data: Climate data dictionary
    
    Returns:
        Dict: Filtered climate data with complete records only
    """
    print("Filtering complete records...")
    filtered_data = {}
    
    for coord in climate_data:
        complete_years = {}
        
        for year in climate_data[coord]:
            temp_list, precip_list = climate_data[coord][year]
            
            # Only keep years with complete data for both temperature and precipitation
            if len(temp_list) == 12 and len(precip_list) == 12:
                complete_years[year] = (temp_list, precip_list)
        
        # Only keep coordinate if it has at least one complete year
        if complete_years:
            filtered_data[coord] = complete_years
    
    return filtered_data

def convert_to_json_format(climate_data: Dict[int, Dict[int, Tuple[list, list]]]) -> list:
    """
    Convert climate data to the final JSON format.
    
    Args:
        climate_data: Climate data dictionary
    
    Returns:
        list: List of JSON objects for each location
    """
    json_objects = []
    
    for coord, years_data in climate_data.items():
        if not years_data:  # Skip if no years data
            continue
            
        climate_obj = {
            "ClimateData": {},
            "Coordinate": int(coord)
        }
        
        for year, (temp_list, precip_list) in years_data.items():
            if len(temp_list) == 12 and len(precip_list) == 12:
                climate_obj["ClimateData"][str(year)] = {
                    "Temperatures": temp_list,
                    "Precipitation": precip_list
                }
        
        # Only add if we have at least one complete year
        if climate_obj["ClimateData"]:
            json_objects.append(climate_obj)
    
    return json_objects

def save_to_json_file(json_objects: list, output_file: str):
    """
    Save JSON objects to file, one per line.
    
    Args:
        json_objects (list): List of JSON objects
        output_file (str): Output file path
    """
    with open(output_file, 'w') as f:
        for obj in json_objects:
            json.dump(obj, f, separators=(',', ':'))
            f.write('\n')
    
    print(f"Saved {len(json_objects)} climate records to: {output_file}")

def main():
    """Main function to process parquet files and create JSON output."""
    
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python convert_pq2json.py <temperature_file.parquet> <precipitation_file.parquet>")
        print("Example: python convert_pq2json.py tg_monthly_2020-2022.parquet rr_monthly_2020-2022.parquet")
        return
    
    temp_file = sys.argv[1]
    precip_file = sys.argv[2]
    
    print("Converting parquet files to JSON format...")
    print(f"Temperature file: {temp_file}")
    print(f"Precipitation file: {precip_file}")
    print("-" * 60)
    
    try:
        # Step 1: Load and process temperature data
        print("Step 1: Loading temperature data...")
        temp_df = load_parquet_file(temp_file)
        
        print("Transforming temperature data...")
        temp_transformed = transform_data(temp_df, 'temperature')
        print(f"Temperature data transformed: {temp_transformed.shape}")
        
        print("Creating temperature dictionary...")
        climate_data = create_temperature_dictionary(temp_transformed)
        
        # Free temperature memory
        del temp_df, temp_transformed
        print(f"Temperature processing complete. Found {len(climate_data)} locations.")
        
        # Step 2: Load and process precipitation data
        print(f"\n{'-' * 60}")
        print("Step 2: Loading precipitation data...")
        precip_df = load_parquet_file(precip_file)
        
        print("Transforming precipitation data...")
        precip_transformed = transform_data(precip_df, 'precipitation')
        print(f"Precipitation data transformed: {precip_transformed.shape}")
        
        print("Updating dictionary with precipitation data...")
        climate_data = update_with_precipitation(climate_data, precip_transformed)
        
        # Free precipitation memory
        del precip_df, precip_transformed
        
        # Step 3: Filter complete records
        print(f"\n{'-' * 60}")
        print("Step 3: Filtering complete records...")
        climate_data = filter_complete_records(climate_data)
        
        print(f"Found {len(climate_data)} locations with complete data")
        
        # Calculate total years across all locations
        total_location_years = sum(len(years) for years in climate_data.values())
        print(f"Total location-year combinations: {total_location_years}")
        
        print(f"\n{'-' * 60}")
        print("Converting to JSON format...")
        
        # Convert to JSON format
        json_objects = convert_to_json_format(climate_data)
        
        print(f"Created {len(json_objects)} JSON objects")
        
        # Save to file
        output_file = "climate_data.json"
        save_to_json_file(json_objects, output_file)
        
        # Show file size
        file_size = Path(output_file).stat().st_size / (1024*1024)
        print(f"Output file size: {file_size:.2f} MB")
        
        # Show sample of first record
        if json_objects:
            print(f"\n{'-' * 60}")
            print("Sample record (first location):")
            sample = json_objects[0]
            coord = sample["Coordinate"]
            lat, lon = decode_coordinates(coord)
            print(f"Coordinate: {coord} (lat: {lat:.5f}, lon: {lon:.5f})")
            years = list(sample["ClimateData"].keys())
            print(f"Years available: {len(years)} ({min(years)}-{max(years)})")
            
            # Show first year data
            if years:
                first_year = min(years)
                first_year_data = sample["ClimateData"][first_year]
                print(f"Sample year {first_year}:")
                print(f"  Temperatures: {first_year_data['Temperatures']}")
                print(f"  Precipitation: {first_year_data['Precipitation']}")
    
    except Exception as e:
        print(f"Error: {e}")
        return

if __name__ == "__main__":
    main()