#!/usr/bin/env python3
"""
Script to detect first autumn frost patterns in Poland and create animated visualizations.
Analyzes daily minimum temperature data to find first frost (below -1°C) occurrence
for 5-year periods and creates maps showing temporal changes.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from scipy.interpolate import griddata
from pathlib import Path
import argparse
from datetime import datetime, timedelta
import warnings
from PIL import Image
import imageio

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Poland bounding box (same as in extract script)
POLAND_BOUNDS = {
    'lon_min': 14.0,
    'lon_max': 24.5,
    'lat_min': 45.0,
    'lat_max': 55.0
}

# Frost threshold
FROST_THRESHOLD = 0.0  # °C

# Fixed date range for consistent color scale across all maps
FROST_SEASON_START_DAY = 244  # September 1st (day 244)
FROST_SEASON_END_DAY = 334    # November 30th (day 334)

def load_temperature_data(file_path):
    """
    Load temperature data from parquet file.
    
    Args:
        file_path (str): Path to the parquet file with temperature data
        
    Returns:
        pd.DataFrame: Temperature data with columns [longitude, latitude, time, min_temp]
    """
    print(f"Loading temperature data from: {file_path}")
    df = pd.read_parquet(file_path)
    
    # Ensure time column is datetime
    df['time'] = pd.to_datetime(df['time'])
    
    # Add useful date columns
    df['year'] = df['time'].dt.year
    df['month'] = df['time'].dt.month
    df['day_of_year'] = df['time'].dt.dayofyear
    
    print(f"Loaded {len(df):,} records")
    print(f"Date range: {df['time'].min()} to {df['time'].max()}")
    print(f"Temperature range: {df['min_temp'].min():.1f}°C to {df['min_temp'].max():.1f}°C")
    
    return df

def define_autumn_period():
    """
    Define the autumn period for frost detection (September 1 - December 31).
    
    Returns:
        tuple: (start_day_of_year, end_day_of_year)
    """
    # September 1st is typically day 244 (or 245 in leap years)
    # December 31st is day 365 (or 366 in leap years)
    # We'll use approximate values and handle leap years in processing
    return (244, 365)

def detect_first_frost_by_period(df, period_years=3, period_step=3, start_year=None, end_year=None):
    """
    Detect first autumn frost for each location and time period using non-overlapping windows.
    
    Args:
        df (pd.DataFrame): Temperature data
        period_years (int): Number of years per period (default: 3)
        period_step (int): Step size between period starts (default: 3, non-overlapping)
        start_year (int): Start year for analysis (optional)
        end_year (int): End year for analysis (optional)
        
    Returns:
        pd.DataFrame: First frost data with columns [longitude, latitude, period, first_frost_day, avg_first_frost]
    """
    print(f"Detecting first frost patterns using {period_years}-year periods with {period_step}-year steps...")
    
    # Filter for autumn months (September to December)
    autumn_data = df[df['month'].isin([9, 10, 11, 12])].copy()
    
    # Define non-overlapping periods
    data_min_year = autumn_data['year'].min()
    data_max_year = autumn_data['year'].max()
    
    # Use provided start/end years or default to data range
    analysis_start_year = start_year if start_year is not None else data_min_year
    analysis_end_year = end_year if end_year is not None else data_max_year
    
    # Ensure the years are within the data range
    analysis_start_year = max(analysis_start_year, data_min_year)
    analysis_end_year = min(analysis_end_year, data_max_year)
    
    periods = []
    current_start_year = analysis_start_year
    while current_start_year + period_years - 1 <= analysis_end_year:
        current_end_year = current_start_year + period_years - 1
        periods.append((current_start_year, current_end_year))
        current_start_year += period_step
    
    print(f"Analyzing {len(periods)} non-overlapping periods: {periods}")
    
    frost_results = []
    
    for start_year, end_year in periods:
        period_name = f"{start_year}-{end_year}"
        print(f"Processing period: {period_name}")
        
        # Filter data for this period
        period_data = autumn_data[
            (autumn_data['year'] >= start_year) & 
            (autumn_data['year'] <= end_year)
        ].copy()
        
        if len(period_data) == 0:
            continue
        
        # For each location and year, find first frost day
        location_year_frost = []
        
        for (lon, lat), location_data in period_data.groupby(['longitude', 'latitude']):
            for year, year_data in location_data.groupby('year'):
                # Sort by day of year to find first occurrence
                year_data_sorted = year_data.sort_values('day_of_year')
                
                # Find first day with temperature < frost threshold (below 0°C)
                frost_days = year_data_sorted[year_data_sorted['min_temp'] < FROST_THRESHOLD]
                
                if len(frost_days) > 0:
                    first_frost_day = frost_days.iloc[0]['day_of_year']
                    first_frost_date = frost_days.iloc[0]['time']
                    
                    location_year_frost.append({
                        'longitude': lon,
                        'latitude': lat,
                        'year': year,
                        'first_frost_day': first_frost_day,
                        'first_frost_date': first_frost_date,
                        'period': period_name
                    })
        
        # Convert to DataFrame and calculate averages per location
        if location_year_frost:
            period_frost_df = pd.DataFrame(location_year_frost)
            
            # Calculate average first frost day for each location in this period
            location_avg = period_frost_df.groupby(['longitude', 'latitude']).agg({
                'first_frost_day': 'mean',
                'period': 'first'
            }).reset_index()
            
            location_avg.columns = ['longitude', 'latitude', 'avg_first_frost_day', 'period']
            frost_results.append(location_avg)
    
    if frost_results:
        final_df = pd.concat(frost_results, ignore_index=True)
        print(f"Found frost data for {len(final_df)} location-period combinations")
        return final_df
    else:
        print("No frost data found!")
        return pd.DataFrame()

def day_of_year_to_date_string(day_of_year):
    """
    Convert day of year to a readable date string (assuming non-leap year).
    
    Args:
        day_of_year (float): Day of year (1-365)
        
    Returns:
        str: Date string in format "MMM DD"
    """
    try:
        # Use 2023 as reference year (non-leap)
        date = datetime(2023, 1, 1) + timedelta(days=int(day_of_year) - 1)
        return date.strftime("%b %d")
    except:
        return f"Day {int(day_of_year)}"

def create_frost_map(frost_data, period, output_dir):
    """
    Create a continuous interpolated map showing first frost patterns for a specific period.
    Uses fixed color scale from Sep 1 to Nov 30 for consistency across all maps.
    
    Args:
        frost_data (pd.DataFrame): Frost data for one period
        period (str): Period name (e.g., "1980-1986")
        output_dir (Path): Output directory for saving maps
        
    Returns:
        str: Path to saved map file
    """
    if len(frost_data) == 0:
        print(f"No data for period {period}")
        return None
    
    # Create figure with cartopy projection
    fig = plt.figure(figsize=(12, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())
    
    # Set extent to Poland with some padding
    padding = 0.5
    extent = [
        POLAND_BOUNDS['lon_min'] - padding,
        POLAND_BOUNDS['lon_max'] + padding,
        POLAND_BOUNDS['lat_min'] - padding,
        POLAND_BOUNDS['lat_max'] + padding
    ]
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    
    # Add map features
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, color='black')
    ax.add_feature(cfeature.BORDERS, linewidth=0.8, color='black')
    ax.add_feature(cfeature.OCEAN, color='lightblue', alpha=0.3)
    ax.add_feature(cfeature.LAND, color='lightgray', alpha=0.2)
    
    # Prepare data for interpolation
    points = frost_data[['longitude', 'latitude']].values
    values = frost_data['avg_first_frost_day'].values
    
    # Create regular grid for interpolation
    lon_min, lon_max, lat_min, lat_max = extent
    resolution = 100  # Grid resolution
    lon_grid = np.linspace(lon_min, lon_max, resolution)
    lat_grid = np.linspace(lat_min, lat_max, resolution)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
    
    # Interpolate data onto regular grid
    try:
        grid_values = griddata(
            points, values, (lon_mesh, lat_mesh), 
            method='cubic', fill_value=np.nan
        )
    except:
        # Fallback to linear interpolation if cubic fails
        grid_values = griddata(
            points, values, (lon_mesh, lat_mesh), 
            method='linear', fill_value=np.nan
        )
    
    # Use FIXED color scale from Sep 1 to Nov 30 for consistency across all maps
    min_day = FROST_SEASON_START_DAY  # Sep 1
    max_day = FROST_SEASON_END_DAY    # Nov 30
    
    # Create HSV colormap: early frost (purple/blue) -> late frost (red/orange)
    # Map day range to hue values: 0.8 (purple) to 0.0 (red)
    n_colors = 256
    hue_start = 0.8  # Purple/Blue
    hue_end = 0.0    # Red
    
    # Create HSV color array
    hsv_colors = np.zeros((n_colors, 3))
    hsv_colors[:, 0] = np.linspace(hue_start, hue_end, n_colors)  # Hue
    hsv_colors[:, 1] = 0.9  # Saturation (high)
    hsv_colors[:, 2] = 0.9  # Value (bright)
    
    # Convert HSV to RGB
    from matplotlib.colors import hsv_to_rgb
    rgb_colors = hsv_to_rgb(hsv_colors.reshape(1, n_colors, 3)).reshape(n_colors, 3)
    
    # Create colormap
    cmap = mcolors.ListedColormap(rgb_colors)
    
    # Create contour plot for smooth continuous visualization using FIXED levels
    levels = np.linspace(min_day, max_day, 50)
    contour = ax.contourf(
        lon_mesh, lat_mesh, grid_values,
        levels=levels,
        cmap=cmap,
        extend='both',
        alpha=0.8,
        transform=ccrs.PlateCarree(),
        vmin=min_day,
        vmax=max_day
    )
    
    # Add original data points as small dots for reference
    ax.scatter(
        frost_data['longitude'],
        frost_data['latitude'],
        c='black',
        s=1,
        alpha=0.3,
        transform=ccrs.PlateCarree()
    )
    
    # Add colorbar with FIXED scale
    cbar = plt.colorbar(contour, ax=ax, orientation='horizontal', pad=0.05, shrink=0.8)
    cbar.set_label('First Frost Day of Year', fontsize=12, fontweight='bold')
    
    # Create custom tick labels showing dates (FIXED positions from Sep 1 to Nov 30)
    tick_positions = np.linspace(FROST_SEASON_START_DAY, FROST_SEASON_END_DAY, 7)  # 7 ticks for better spacing
    tick_labels = [day_of_year_to_date_string(day) for day in tick_positions]
    cbar.set_ticks(tick_positions)
    cbar.set_ticklabels(tick_labels)
    
    # Add title
    plt.title(f'First Autumn Frost in Poland - {period}', 
              fontsize=16, fontweight='bold', pad=20)
    
    # Add period as prominent caption
    ax.text(0.02, 0.98, period, transform=ax.transAxes, fontsize=20, 
            fontweight='bold', color='black', bbox=dict(boxstyle='round,pad=0.5', 
            facecolor='white', alpha=0.9), verticalalignment='top')
    
    # Save the map
    output_file = output_dir / f'frost_map_{period}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"Created map for {period}: {output_file}")
    return str(output_file)

def create_animated_gif(image_files, output_path, duration=2.0):
    """
    Create an animated GIF from a list of image files.
    
    Args:
        image_files (list): List of image file paths
        output_path (str): Output path for the GIF
        duration (float): Duration per frame in seconds
    """
    if not image_files:
        print("No image files to create GIF")
        return
    
    print(f"Creating animated GIF with {len(image_files)} frames...")
    
    # Load images
    images = []
    for img_path in sorted(image_files):
        if Path(img_path).exists():
            img = Image.open(img_path)
            images.append(img)
    
    if not images:
        print("No valid images found for GIF creation")
        return
    
    # Save as GIF
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=int(duration * 1000),  # Convert to milliseconds
        loop=0  # Infinite loop
    )
    
    print(f"Created animated GIF: {output_path}")

def create_trend_analysis(frost_data, output_dir):
    """
    Create additional analysis plots showing trends over time (saved to file, no display).
    
    Args:
        frost_data (pd.DataFrame): All frost data
        output_dir (Path): Output directory
    """
    if len(frost_data) == 0:
        return
    
    print("Creating trend analysis...")
    
    # Calculate average frost day for each period
    period_stats = frost_data.groupby('period').agg({
        'avg_first_frost_day': ['mean', 'std', 'count']
    }).round(1)
    
    period_stats.columns = ['mean_frost_day', 'std_frost_day', 'location_count']
    period_stats = period_stats.reset_index()
    
    # Extract start year from period for plotting
    period_stats['start_year'] = period_stats['period'].str.split('-').str[0].astype(int)
    
    # Create trend plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Average first frost day over time
    ax1.errorbar(period_stats['start_year'], period_stats['mean_frost_day'], 
                yerr=period_stats['std_frost_day'], marker='o', linewidth=2, 
                capsize=5, capthick=2, markersize=8)
    ax1.set_xlabel('Period Start Year', fontsize=12)
    ax1.set_ylabel('Average First Frost Day of Year', fontsize=12)
    ax1.set_title('Temporal Trend of First Autumn Frost in Poland', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Add secondary y-axis with dates
    ax1_dates = ax1.twinx()
    y_ticks = ax1.get_yticks()
    date_labels = [day_of_year_to_date_string(day) for day in y_ticks]
    ax1_dates.set_yticks(y_ticks)
    ax1_dates.set_yticklabels(date_labels)
    ax1_dates.set_ylabel('Approximate Date', fontsize=12)
    
    # Plot 2: Number of locations per period
    ax2.bar(period_stats['start_year'], period_stats['location_count'], 
            alpha=0.7, color='skyblue', edgecolor='black')
    ax2.set_xlabel('Period Start Year', fontsize=12)
    ax2.set_ylabel('Number of Locations', fontsize=12)
    ax2.set_title('Data Coverage by Period', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save trend analysis
    trend_file = output_dir / 'frost_trend_analysis.png'
    plt.savefig(trend_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"Created trend analysis: {trend_file}")
    
    # Save statistics to CSV
    stats_file = output_dir / 'frost_statistics.csv'
    period_stats.to_csv(stats_file, index=False)
    print(f"Saved statistics: {stats_file}")

def main():
    """Main function to process frost detection and create visualizations."""
    parser = argparse.ArgumentParser(description="Detect first autumn frost patterns in Poland and create animated visualizations.")
    parser.add_argument("--data_file", required=True, 
                        help="Path to the parquet file with daily temperature data.")
    parser.add_argument("--output_dir", default="frost_analysis", 
                        help="Output directory for maps and animations (default: frost_analysis).")
    parser.add_argument("--period_years", type=int, default=3, 
                        help="Number of years per analysis period (default: 3).")
    parser.add_argument("--start_year", type=int, 
                        help="Start year for analysis (optional, defaults to first available year).")
    parser.add_argument("--end_year", type=int, 
                        help="End year for analysis (optional, defaults to last available year).")
    parser.add_argument("--gif_duration", type=float, default=2.0, 
                        help="Duration per frame in animated GIF (seconds, default: 2.0).")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print("FIRST AUTUMN FROST ANALYSIS FOR POLAND")
    
    # Load temperature data
    df = load_temperature_data(args.data_file)
    
    # Detect first frost patterns with non-overlapping windows
    frost_data = detect_first_frost_by_period(df, args.period_years, period_step=args.period_years, 
                                            start_year=args.start_year, end_year=args.end_year)
    
    if len(frost_data) == 0:
        print("No frost data found. Exiting.")
        return
    
    # Create maps for each period
    print("\nCreating frost maps...")
    image_files = []
    
    for period in sorted(frost_data['period'].unique()):
        period_data = frost_data[frost_data['period'] == period]
        map_file = create_frost_map(period_data, period, output_dir)
        if map_file:
            image_files.append(map_file)
    
    # Create animated GIF
    if image_files:
        gif_path = output_dir / 'frost_animation.gif'
        create_animated_gif(image_files, gif_path, args.gif_duration)
    
    # Create trend analysis
    create_trend_analysis(frost_data, output_dir)
    
    print(f"ANALYSIS COMPLETE")
    print(f"Output directory: {output_dir}")
    print(f"Created {len(image_files)} maps")
    print(f"Animated GIF: {output_dir / 'frost_animation.gif'}")
    print(f"Trend analysis: {output_dir / 'frost_trend_analysis.png'}")

if __name__ == "__main__":
    main()