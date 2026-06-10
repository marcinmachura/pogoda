"""Plot Koppen classifications for a year range on a map of Europe.

Reads CSV produced by the F# program (format: Lat,Lon,year,koppen,trewartha).
Defaults to /tmp/climate_classifications.csv and year range 2018-2023.

The script will try to use cartopy for a proper map projection and coastlines.
If cartopy is not available it will fall back to a simple lon/lat scatter plot.

Can generate individual images for each year and optionally create an animation.

Usage:
    python create_plots.py --csv /tmp/climate_classifications.csv --start-year 2018 --end-year 2023 --output-dir ./output --animation

Requirements (recommended):
    pip install pandas matplotlib cartopy pillow

"""
import argparse
import sys
import os
from collections import OrderedDict
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Try to import PIL for animation creation
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try to import cartopy for nicer maps; fall back if unavailable
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except Exception:
    HAS_CARTOPY = False


# Color scheme (simplified) for Koppen classes based on common Wikipedia palettes.
# Mapping uses prefixes (e.g., 'Cfb' -> 'C', 'Af' -> 'A', 'BWk' -> 'BW') with some more specific entries.
KOPPEN_COLORS = OrderedDict([
    ("Af", "#0000FE"),
    ("Am", "#0077ff"),
    ("Aw", "#46a9fa"),
    ("As", "#79baec"),
    ("BWh", "#Fe0000"),
    ("BWk", "#fe9695"),
    ("BSh", "#f5a301"),
    ("BSk", "#ffdb63"),
    ("Csa", "#FFFF00"),
    ("Csb", "#C6C700"),
    ("Csc", "#969600"),
    ("Cwa", "#96ff96"),
    ("Cwb", "#63c764"),
    ("Cwc", "#329633"),
    ("Cfa", "#c6ff4e"),
    ("Cfb", "#66ff33"),
    ("Cfc", "#33c701"),
    ("Dsa", "#FF00fe"),
    ("Dsb", "#c600c7"),
    ("Dsc", "#963295"),
    ("Dsd", "#966495"),
    ("Dwa", "#ABB1FF"),
    ("Dwb", "#6a77db"),
    ("Dwc", "#004080"),
    ("Dwd", "#320087"),
    ("Dfa", "#00FFFF"),
    ("Dfb", "#38c7ff"),
    ("Dfc", "#007e7d"),
    ("Dfd", "#00455e"),
    ("ET", "#C0C0C0"),
    ("EF", "#80A0B4"),
    # Fallback
    ("other", "#777777"),
])


def map_koppen_to_color(code: str) -> str:
    if not isinstance(code, str) or code == "":
        return KOPPEN_COLORS["other"]
    # Prefer exact matches (3-letter codes), then 2-letter prefixes, then first letter
    for key in KOPPEN_COLORS.keys():
        if key == "other":
            continue
        if code == key:
            return KOPPEN_COLORS[key]
    # try 3-letter prefix
    if len(code) >= 3:
        prefix3 = code[:3]
        if prefix3 in KOPPEN_COLORS:
            return KOPPEN_COLORS[prefix3]
    # try 2-letter prefix
    if len(code) >= 2:
        prefix2 = code[:2]
        if prefix2 in KOPPEN_COLORS:
            return KOPPEN_COLORS[prefix2]
    # first letter
    first = code[0]
    if first in KOPPEN_COLORS:
        return KOPPEN_COLORS[first]
    return KOPPEN_COLORS["other"]


def build_legend(ax, unique_codes):
    # Build legend patches
    import matplotlib.patches as mpatches
    patches = []
    for code in unique_codes:
        color = map_koppen_to_color(code)
        patches.append(mpatches.Patch(color=color, label=code))
    ax.legend(handles=patches, loc="lower left", fontsize="small", ncol=2)


def plot_with_cartopy(df, year, out_path, caption=None):
    fig = plt.figure(figsize=(12, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-25, 45, 30, 72], crs=ccrs.PlateCarree())  # Europe-ish extent
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"))
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linestyle=':')
    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f0f0f0")
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#a6cee3")

    # map colors
    colors = df['koppen'].astype(str).apply(map_koppen_to_color)
    sc = ax.scatter(df['lon'], df['lat'], c=colors.tolist(), s=8, alpha=0.8, transform=ccrs.PlateCarree())

    # build legend for the most frequent classes
    top_codes = df['koppen'].astype(str).value_counts().head(12).index.tolist()
    build_legend(ax, top_codes)

    # Set title with optional custom caption
    if caption:
        ax.set_title(caption, fontsize=18, fontweight='bold', pad=20)
    else:
        ax.set_title(f"Koppen classification, {year}", fontsize=16, fontweight='bold')
    
    # Add year as prominent caption
    ax.text(0.02, 0.98, str(year), transform=ax.transAxes, fontsize=24, 
            fontweight='bold', color='black', bbox=dict(boxstyle='round,pad=0.3', 
            facecolor='white', alpha=0.8), verticalalignment='top')
    
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)


def plot_simple(df, year, out_path, caption=None):
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(-25, 45)
    ax.set_ylim(30, 72)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    
    # Set title with optional custom caption
    if caption:
        ax.set_title(caption, fontsize=18, fontweight='bold', pad=20)
    else:
        ax.set_title(f"Koppen classification (simple), {year}", fontsize=16, fontweight='bold')
    
    colors = df['koppen'].astype(str).apply(map_koppen_to_color)
    #colors = df['trewartha'].astype(str).str[:3].apply(map_koppen_to_color)
    ax.scatter(df['lon'], df['lat'], c=colors.tolist(), s=6, alpha=0.8)
    #top_codes = df['trewartha'].astype(str).str[:3].value_counts().head(12).index.tolist()
    top_codes = df['koppen'].astype(str).value_counts().head(12).index.tolist()
    build_legend(ax, top_codes)
    
    # Add year as prominent caption
    ax.text(0.02, 0.98, str(year), transform=ax.transAxes, fontsize=24, 
            fontweight='bold', color='black', bbox=dict(boxstyle='round,pad=0.3', 
            facecolor='white', alpha=0.8), verticalalignment='top')
    
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)


def create_animation(image_paths, output_path, duration=1000):
    """Create an animated GIF from a list of image paths."""
    if not HAS_PIL:
        print("Warning: PIL/Pillow not available, skipping animation creation")
        return False
    
    try:
        images = []
        for path in image_paths:
            img = Image.open(path)
            images.append(img)
        
        # Save as animated GIF
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=duration,
            loop=0
        )
        return True
    except Exception as e:
        print(f"Error creating animation: {e}")
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', default='/tmp/climate_classifications.csv', help='path to CSV')
    p.add_argument('--start-year', type=int, default=2018, help='start year of range')
    p.add_argument('--end-year', type=int, default=2023, help='end year of range')
    p.add_argument('--output-dir', default='./koppen_output', help='output directory for images')
    p.add_argument('--animation', action='store_true', help='create animated GIF')
    p.add_argument('--animation-duration', type=int, default=1000, help='duration per frame in ms (default: 1000)')
    p.add_argument('--caption', default=None, help='custom caption to display as image header')
    args = p.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading {args.csv} ...")
    df = pd.read_csv(args.csv, usecols=['Lat','Lon','year','koppen','trewartha'], 
                     dtype={'Lat': float, 'Lon': float, 'year': int, 'koppen': str, 'trewartha': str})
    df = df.rename(columns={'Lat': 'lat', 'Lon': 'lon'})
    
    # Filter data for the year range
    year_range = range(args.start_year, args.end_year + 1)
    df_filtered = df[df['year'].isin(year_range)]
    
    if len(df_filtered) == 0:
        print(f'No data for year range {args.start_year}-{args.end_year}')
        sys.exit(1)

    print(f"Total rows for year range {args.start_year}-{args.end_year}: {len(df_filtered)}")
    
    image_paths = []
    
    # Generate images for each year
    for year in year_range:
        print(f"\nProcessing year {year}...")
        df_year = df_filtered[df_filtered['year'] == year]
        
        if len(df_year) == 0:
            print(f'No data for year {year}, skipping...')
            continue
            
        print(f"Rows for year {year}: {len(df_year)}")
        
        # Optionally reduce point count for faster rendering (sample if huge)
        if len(df_year) > 200000:
            print('Large number of points, sampling 200k for plotting...')
            df_year = df_year.sample(n=200000, random_state=1)

        # Generate output path
        out_path = output_dir / f"koppen_{year}.png"
        
        # Create the plot
        if HAS_CARTOPY:
            print('Using cartopy for map rendering')
            plot_with_cartopy(df_year, year, str(out_path), args.caption)
        else:
            print('Cartopy not available, using simple scatter')
            plot_simple(df_year, year, str(out_path), args.caption)

        print(f'Wrote map image to {out_path}')
        image_paths.append(str(out_path))
    
    # Create animation if requested
    if args.animation and image_paths:
        animation_path = output_dir / f"koppen_animation_{args.start_year}_{args.end_year}.gif"
        print(f"\nCreating animation: {animation_path}")
        
        if create_animation(image_paths, str(animation_path), args.animation_duration):
            print(f"Animation created successfully: {animation_path}")
        else:
            print("Failed to create animation")
    
    print(f"\nCompleted! Generated {len(image_paths)} images in {output_dir}")


if __name__ == '__main__':
    main()
