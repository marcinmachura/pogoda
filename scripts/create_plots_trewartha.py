"""Plot Trewartha classifications for a year range on a map of Europe.

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
import matplotlib.colors as mcolors

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


# Trewartha color scheme ordered by frequency from trewartha_codes.txt
# Most frequent codes first, then less common ones
TREWARTHA_COLORS = OrderedDict([
    # Most frequent codes (from trewartha_codes.txt)
    ("Dc", "#0000FE"),     # Dcbo/Dclo - 35.4% combined
    ("Ec", "#900090"),     # Eclc - 13.8%
    ("Do", "#007700"),     # Dobk/Doak - 11.7% combined  
    ("Eo", "#083008"),     # Eolo/Eolk/Eolc - 8.1% combined
    ("Cs", "#FFFF00"),     # Csak/Csal/Cshk/Csbl/Cshl - 7.9% combined
    ("Ft", "#707070"),     # Ftko/Ftkc/Ftkk - 3.2% combined (fixed invalid hex)
    ("Cf", "#c6ff4e"),     # Cfak/Cfbk/Cflk/Cfbl - 0.7% combined
    ("BW", "#Fe0000"),     # BWhl/BWhk/BWak/BWal/BWbk/BWab/BWbl/BWll/BWlk/BWil - 1.0% combined
    ("BS", "#f5a301"),     # BSal/BShk/BShl/BSak/BSab/BShb/BWhb/BSbk/BSil/BSik/BSbl/BSao/BSlk - 1.4% combined
    ("Cw", "#96ff96"),     # Cwak/Cwbk/Cwal - rare
    
    # Less common original Koppen codes (keeping for compatibility)
    ("Df", "#00AAAA"),     # From original Koppen
    ("Dw", "#ABB1FF"),     # From original Koppen  
    ("Ds", "#FF00fe"),     # From original Koppen
    ("ET", "#807034"),     # From original Koppen
    ("EF", "#407034"),     # From original Koppen
    ("Af", "#507034"),     # From original Koppen
    ("Am", "#300064"),     # From original Koppen
    ("Aw", "#003064"),     # From original Koppen
    ("As", "#700064"),     # From original Koppen
    
    # Fallback
    ("other", "#FFFFFF"),
])


def adjust_color_hsv(hex_color: str, brightness_factor: float = 1.0, saturation_factor: float = 1.0) -> str:
    """Adjust brightness and saturation of a hex color using HSV color space."""
    try:
        # Convert hex to RGB
        rgb = mcolors.hex2color(hex_color)
        # Convert RGB to HSV
        hsv = mcolors.rgb_to_hsv(rgb)
        
        # Adjust saturation (index 1) and value/brightness (index 2)
        hsv = list(hsv)
        hsv[1] = max(0.0, min(1.0, hsv[1] * saturation_factor))  # Clamp saturation to [0,1]
        hsv[2] = max(0.0, min(1.0, hsv[2] * brightness_factor))  # Clamp brightness to [0,1]
        
        # Convert back to RGB then hex
        rgb_adjusted = mcolors.hsv_to_rgb(hsv)
        return mcolors.rgb2hex(rgb_adjusted)
    except (ValueError, TypeError) as e:
        print(f"Warning: Color conversion failed for {hex_color}: {e}")
        return hex_color  # Return original if conversion fails


def get_brightness_factor(third_letter: str) -> float:
    """Get brightness adjustment factor based on 3rd letter (+/-20%)."""
    brightness_map = {
        'a': 1.2,   # +20% brighter
        'b': 1.1,   # +10% brighter  
        'c': 1.0,   # baseline
        'd': 0.9,   # -10% darker
        'e': 0.8,   # -20% darker
        'f': 0.85,  # -15% darker
        'g': 0.95,  # -5% darker
        'h': 1.05,  # +5% brighter
        'i': 1.15,  # +15% brighter
        'j': 0.75,  # -25% darker
        'k': 1.0,   # baseline
        'l': 0.9,   # -10% darker
        'm': 1.1,   # +10% brighter
        'n': 0.95,  # -5% darker
        'o': 1.05,  # +5% brighter
        'p': 0.85,  # -15% darker
        'q': 1.15,  # +15% brighter
        'r': 0.8,   # -20% darker
        's': 1.2,   # +20% brighter
        't': 0.9,   # -10% darker
        'u': 1.1,   # +10% brighter
        'v': 0.85,  # -15% darker
        'w': 1.05,  # +5% brighter
        'x': 0.95,  # -5% darker
        'y': 1.15,  # +15% brighter
        'z': 0.8,   # -20% darker
    }
    return brightness_map.get(third_letter.lower(), 1.0)


def get_saturation_factor(fourth_letter: str) -> float:
    """Get saturation adjustment factor based on 4th letter (+/-10%)."""
    saturation_map = {
        'a': 1.1,   # +10% more saturated
        'b': 1.05,  # +5% more saturated
        'c': 1.0,   # baseline
        'd': 0.95,  # -5% less saturated
        'e': 0.9,   # -10% less saturated
        'f': 0.92,  # -8% less saturated
        'g': 1.02,  # +2% more saturated
        'h': 0.98,  # -2% less saturated
        'i': 1.08,  # +8% more saturated
        'j': 0.88,  # -12% less saturated
        'k': 1.0,   # baseline
        'l': 0.93,  # -7% less saturated
        'm': 1.07,  # +7% more saturated
        'n': 0.96,  # -4% less saturated
        'o': 1.04,  # +4% more saturated
        'p': 0.91,  # -9% less saturated
        'q': 1.09,  # +9% more saturated
        'r': 0.89,  # -11% less saturated
        's': 1.1,   # +10% more saturated
        't': 0.94,  # -6% less saturated
        'u': 1.06,  # +6% more saturated
        'v': 0.92,  # -8% less saturated
        'w': 1.03,  # +3% more saturated
        'x': 0.97,  # -3% less saturated
        'y': 1.08,  # +8% more saturated
        'z': 0.9,   # -10% less saturated
    }
    return saturation_map.get(fourth_letter.lower(), 1.0)


def map_trewartha_to_color(code: str) -> str:
    if not isinstance(code, str) or code == "":
        return TREWARTHA_COLORS["other"]
    
    # Get base color from 2-letter prefix
    base_color = None
    if len(code) >= 2:
        prefix2 = code[:2]
        if prefix2 in TREWARTHA_COLORS:
            base_color = TREWARTHA_COLORS[prefix2]
    
    # Fallback to first letter if 2-letter not found
    if base_color is None and len(code) >= 1:
        first = code[0]
        if first in TREWARTHA_COLORS:
            base_color = TREWARTHA_COLORS[first]
    
    if base_color is None:
        base_color = TREWARTHA_COLORS["other"]
    
    # Apply brightness adjustment based on 3rd letter
    brightness_factor = 1.0
    if len(code) >= 3:
        brightness_factor = get_brightness_factor(code[2])
    
    # Apply saturation adjustment based on 4th letter  
    saturation_factor = 1.0
    if len(code) >= 4:
        saturation_factor = get_saturation_factor(code[3])
    
    # Adjust the color
    if brightness_factor != 1.0 or saturation_factor != 1.0:
        return adjust_color_hsv(base_color, brightness_factor, saturation_factor)
    
    return base_color


def build_legend(ax, unique_codes):
    # Build legend patches
    import matplotlib.patches as mpatches
    patches = []
    for code in unique_codes:
        color = map_trewartha_to_color(code)
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

    # map colors using Trewartha color mapping
    colors = df['trewartha'].astype(str).apply(map_trewartha_to_color)
    sc = ax.scatter(df['lon'], df['lat'], c=colors.tolist(), s=8, alpha=0.8, transform=ccrs.PlateCarree())

    # build legend for the most frequent 4-letter codes (top 30)
    top_codes = df['trewartha'].astype(str).value_counts().head(30).index.tolist()
    build_legend(ax, top_codes)

    # Set title with optional custom caption
    if caption:
        ax.set_title(caption, fontsize=18, fontweight='bold', pad=20)
    else:
        ax.set_title(f"Trewartha classification, {year}", fontsize=16, fontweight='bold')
    
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
        ax.set_title(f"Trewartha classification (simple), {year}", fontsize=16, fontweight='bold')
    
    # Use Trewartha color mapping
    colors = df['trewartha'].astype(str).apply(map_trewartha_to_color)
    ax.scatter(df['lon'], df['lat'], c=colors.tolist(), s=6, alpha=0.8)
    
    # Legend based on top 30 4-letter codes
    top_codes = df['trewartha'].astype(str).value_counts().head(30).index.tolist()
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
        out_path = output_dir / f"trewartha_{year}.png"
        
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
