#!/usr/bin/env python3
"""
Script to extract daily minimum temperature data for Poland from NetCDF files.
"""

import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import sys

# Poland bounding box coordinates (approximate)
POLAND_BOUNDS = {
    'lon_min': 14.0,  # Western boundary
    'lon_max': 24.5,  # Eastern boundary
    'lat_min': 44.0,  # Southern boundary
    'lat_max': 55.0   # Northern boundary
}

def read_netcdf_years(file_path):
    """
    Read NetCDF file and extract all available years from the time dimension.
    
    Args:
        file_path (str): Path to the NetCDF file
        
    Returns:
        list: Sorted list of unique years in the dataset
    """
    try:
        # Open the NetCDF file
        ds = xr.open_dataset(file_path)
        
        # Get the time coordinate
        time_coord = ds.time
        
        # Convert to pandas datetime if not already
        if hasattr(time_coord, 'to_pandas'):
            time_series = time_coord.to_pandas()
        else:
            time_series = pd.to_datetime(time_coord.values)
        
        # Extract unique years
        years = sorted(time_series.dt.year.unique())
        
        # Close the dataset
        ds.close()
        
        return years
        
    except Exception as e:
        print(f"Error reading NetCDF file: {e}")
        return []

def process_all_years(file_path, output_file=None, start_year=None, end_year=None):
    """
    Process all years in the NetCDF file and extract daily minimum temperature data for Poland.
    Memory-efficient approach that processes one year at a time.
    
    Args:
        file_path (str): Path to the NetCDF file
        output_file (str): Output parquet file path (optional)
        start_year (int): Start year (optional, processes from first available year if None)
        end_year (int): End year (optional, processes to last available year if None)
    """
    try:
        # Get available years
        years = read_netcdf_years(file_path)
        if not years:
            print("No years found in dataset.")
            return
        
        # Filter years based on start_year and end_year
        if start_year:
            years = [y for y in years if y >= start_year]
        if end_year:
            years = [y for y in years if y <= end_year]
        
        if not years:
            print("No years found in specified range.")
            return
        
        # Generate output filename if not provided
        if output_file is None:
            file_stem = Path(file_path).stem.replace('_ens_mean_0.1deg_reg_v31.0e', '').replace('_ens_mean_0.25deg_reg_2011-2024_v31.0e', '').replace('_ens_mean_0.25deg_reg_v31.0e', '')
            range_suffix = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0])
            output_file = f"{file_stem}_poland_daily_{range_suffix}.parquet"
        
        print(f"Processing {len(years)} years: {min(years)}-{max(years)}")
        print(f"Output file: {output_file}")
        print(f"Poland bounds: {POLAND_BOUNDS}")
        print("-" * 60)
        
        # Remove existing output file if it exists
        if Path(output_file).exists():
            Path(output_file).unlink()
            print(f"Removed existing file: {output_file}")
        
        total_records = 0
        
        # Process each year individually to minimize memory usage
        for i, year in enumerate(years):
            print(f"Processing year {year} ({i+1}/{len(years)})...")
            
            # Process year and get DataFrame
            df_year = process_single_year(file_path, year)
            
            if df_year is not None and len(df_year) > 0:
                # Append to parquet file
                if i == 0:
                    # First year: create new file
                    df_year.to_parquet(output_file, index=False)
                else:
                    # Subsequent years: append to existing file
                    # Read existing data, concatenate, and write back
                    # This is memory-efficient for reasonable file sizes
                    existing_df = pd.read_parquet(output_file)
                    combined_df = pd.concat([existing_df, df_year], ignore_index=True)
                    combined_df.to_parquet(output_file, index=False)
                    del existing_df, combined_df  # Free memory
                
                total_records += len(df_year)
                print(f"  Added {len(df_year)} records (Total: {total_records})")
                
                # Free memory
                del df_year
            else:
                print(f"  No valid data for year {year}")
        
        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total records saved: {total_records}")
        print(f"Output file: {output_file}")
        print(f"File size: {Path(output_file).stat().st_size / (1024*1024):.2f} MB")
        
    except Exception as e:
        print(f"Error processing all years: {e}")

def process_single_year(file_path, year):
    """
    Process a single year and return daily minimum temperature data for Poland.
    
    Args:
        file_path (str): Path to the NetCDF file
        year (int): Year to process
        
    Returns:
        pd.DataFrame: Daily temperature DataFrame for Poland or None if failed
    """
    try:
        # Open the NetCDF file
        ds = xr.open_dataset(file_path)
        
        # Filter data for the specific year
        year_data = ds.sel(time=ds.time.dt.year == year)
        
        if len(year_data.time) == 0:
            print(f"    No data found for year {year}")
            ds.close()
            return None
        
        # Filter for Poland geographical bounds
        poland_data = year_data.sel(
            longitude=slice(POLAND_BOUNDS['lon_min'], POLAND_BOUNDS['lon_max']),
            latitude=slice(POLAND_BOUNDS['lat_min'], POLAND_BOUNDS['lat_max'])
        )
        
        if poland_data.tn.size == 0:
            print(f"    No data in Poland bounds for year {year}")
            ds.close()
            return None
        
        # Filter out NaN values before converting to DataFrame
        data_var = poland_data['tn']
        valid_mask = ~data_var.isnull()
        poland_data_filtered = poland_data.where(valid_mask, drop=True)
        
        if poland_data_filtered['tn'].size == 0:
            print(f"    No valid data after filtering NaN for year {year}")
            ds.close()
            return None
        
        # Convert to DataFrame (keep daily data - no aggregation)
        df = poland_data_filtered.to_dataframe().reset_index()
        df = df.dropna()
        
        # Close dataset to free memory
        ds.close()
        
        if len(df) == 0:
            print(f"    No data after conversion for year {year}")
            return None
        
        # Keep only necessary columns and rename for clarity
        df = df[['longitude', 'latitude', 'time', 'tn']].copy()
        df = df.rename(columns={'tn': 'min_temp'})
        
        print(f"    {len(df)} daily records for Poland")
        
        return df
        
    except Exception as e:
        print(f"    Error processing year {year}: {e}")
        return None

def main():
    """Main function to extract daily minimum temperature data for Poland."""
    parser = argparse.ArgumentParser(description="Extract daily minimum temperature data for Poland from NetCDF files.")
    parser.add_argument("--tn_file", default="tn_ens_mean_0.25deg_reg_v31.0e.nc", 
                        help="Path to the minimum temperature NetCDF file (default: tn_ens_mean_0.25deg_reg_v31.0e.nc).")
    parser.add_argument("--start_year", type=int, help="The first year to process. Defaults to the first available year.")
    parser.add_argument("--end_year", type=int, help="The last year to process. Defaults to the last available year.")
    parser.add_argument("--output", help="Output parquet file path. If not specified, will be auto-generated.")
    
    args = parser.parse_args()

    # --- Process Minimum Temperature Data for Poland ---
    if not Path(args.tn_file).exists():
        print(f"Error: File '{args.tn_file}' not found!")
        sys.exit(1)
        
    print(f"Processing Minimum Temperature file: {args.tn_file}")
    print(f"Extracting daily data for Poland")
    print("-" * 50)
    process_all_years(
        file_path=args.tn_file,
        output_file=args.output,
        start_year=args.start_year, 
        end_year=args.end_year
    )

if __name__ == "__main__":
    main()