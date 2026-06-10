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


# All 4-letter Trewartha codes (from trewartha_codes.txt) grouped by major zone (A-F)
TREWARTHA_CODES_BY_ZONE = OrderedDict({
    'A': [],  # No 'A' codes in the provided list
    'B': [
        'BWhl','BSal','BShk','BShl','BSak','BWhk','BWak','BWal','BSab','BWbk','BShb','BWhb',
        'BWab','BSbk','BSil','BSik','BSbl','BWbl','BWll','BWlk','BSao','BSlk','BWil',
    ],
    'C': [
        'Csak','Csal','Cshk','Csbk','Cfak','Csbl','Cfbk','Cshl','Csik','Csil','Cflk','Cwak',
        'Cslk','Cwbk','Cwal',
    ],
    'D': [
        'Dcbo','Dclo','Dobk','Dolk','Dcao','Doak','Dclc','Dcbc','Dobo','Dohk','Dolo','Doao',
        'Dcho','Dcac','Doho',
    ],
    'E': [
        'Eclc','Eolo','Eolk','Eolc','Ecbc',
    ],
    'F': [
        'Ftko','Ftkc','Ftkk',
    ],
})

def _generate_zone_palette(codes, hue_offset=0.0, saturation=0.92, value=0.88):
    """Generate maximally separated colors for a list of codes by evenly spacing hues."""
    mapping = {}
    n = len(codes)
    if n == 0:
        return mapping
    for i, code in enumerate(codes):
        # Evenly spaced hues around the circle; optional offset per zone
        h = (hue_offset + (i / n)) % 1.0
        r, g, b = mcolors.hsv_to_rgb((h, saturation, value))
        mapping[code] = mcolors.rgb2hex((r, g, b))
    return mapping

# Precompute full hardcoded mapping for all 4-letter codes with zone-specific hue offsets
# Using different offsets per zone isn't strictly required (maps are separate), but helps if compared side-by-side
_ZONE_HUE_OFFSETS = {'A': 0.00, 'B': 0.08, 'C': 0.25, 'D': 0.45, 'E': 0.65, 'F': 0.80}
TREWARTHA_CODE_COLORS = {}
for zone, codes in TREWARTHA_CODES_BY_ZONE.items():
    TREWARTHA_CODE_COLORS.update(
        _generate_zone_palette(codes, hue_offset=_ZONE_HUE_OFFSETS.get(zone, 0.0))
    )


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


def get_moisture_adjustment(second_letter: str) -> tuple[float, float, float]:
    """Adjust RGB toward green (moist) or violet (dry) based on 2nd letter."""
    # Green shift for moist climates, violet shift for dry climates
    moisture_map = {
        'W': (0.7, 0.7, 1.2),  # Dry - shift toward violet
        'S': (0.8, 0.8, 1.1),  # Semi-dry - slight violet shift
        'f': (1.1, 1.2, 0.8),  # Moist year-round - shift toward green
        'w': (1.0, 1.1, 0.9),  # Dry winter - slight green shift
        's': (0.9, 0.9, 1.0),  # Dry summer - slight violet shift
        'T': (0.6, 0.6, 1.3),  # Tundra (dry) - strong violet shift
        'F': (0.5, 0.5, 1.4),  # Ice cap (dry) - very strong violet shift
        'c': (1.1, 1.2, 0.8),  # Cool moist - shift toward green
        'o': (1.0, 1.1, 0.9),  # Oceanic moist - slight green shift
        't': (0.8, 0.8, 1.1),  # Continental dry - slight violet shift
    }
    return moisture_map.get(second_letter.lower(), (1.0, 1.0, 1.0))


def get_moisture_hue_shift(second_letter: str) -> float:
    """Get hue shift in degrees based on moisture (2nd letter).
    Positive = shift toward green (more humid), Negative = shift away from green."""
    moisture_map = {
        # Dry climates - shift away from green
        'W': -60,   # Desert - strong shift away from green
        'S': -40,   # Steppe - moderate shift away from green
        
        # Moist climates - shift toward green
        'f': +60,   # Fully humid - strong shift toward green
        'w': +30,   # Winter dry - moderate shift toward green
        's': +20,   # Summer dry - slight shift toward green
        
        # Special cases
        'T': -80,   # Tundra - very dry, strong shift away
        'F': -90,   # Ice cap - extremely dry
        'c': +40,   # Continental humid - shift toward green
        'o': +50,   # Oceanic - strong shift toward green
        't': -30,   # Continental dry - shift away from green
        'h': +10,   # Humid subtropical - slight green shift
        'a': +25,   # Monsoon-like - moderate green shift
        'b': +35,   # Oceanic subtropical - shift toward green
    }
    return moisture_map.get(second_letter, 0)


def get_summer_brightness(third_letter: str) -> float:
    """Get brightness factor based on summer temperature (3rd letter)."""
    # Map summer temperature letters to brightness (0.3 to 1.0)
    summer_temp_map = {
        'h': 1.0,   # Hot summer - full brightness
        'a': 0.9,   # Warm summer - high brightness
        'b': 0.8,   # Moderate warm summer - good brightness
        'c': 0.7,   # Cool summer - medium brightness
        'd': 0.6,   # Cold summer - low brightness
        'k': 0.5,   # Very cold summer - very low brightness
        'l': 0.4,   # Polar summer - minimal brightness
        'o': 0.75,  # Oceanic moderate - medium-high brightness
        'i': 0.65,  # Continental cool - medium-low brightness
    }
    return summer_temp_map.get(third_letter.lower(), 0.7)


def get_winter_red_blue_balance(fourth_letter: str) -> float:
    """Get red-blue balance based on winter temperature (4th letter).
    Returns value from 0.0 (full blue, very cold) to 1.0 (full red, very hot)."""
    winter_temp_map = {
        'h': 1.0,   # Hot winter - full red
        'a': 0.85,  # Warm winter - strong red
        'b': 0.7,   # Mild winter - moderate red
        'c': 0.55,  # Cool winter - slight red
        'd': 0.4,   # Cold winter - slight blue
        'k': 0.25,  # Very cold winter - moderate blue
        'l': 0.1,   # Extremely cold winter - strong blue
        'o': 0.6,   # Oceanic mild - neutral-warm
        'i': 0.3,   # Continental cold - blue
    }
    return winter_temp_map.get(fourth_letter.lower(), 0.5)


def shift_hue(rgb_color: tuple, hue_shift_degrees: float) -> tuple:
    """Shift the hue of an RGB color by the specified degrees."""
    if hue_shift_degrees == 0:
        return rgb_color
    
    try:
        # Convert RGB to HSV
        hsv = mcolors.rgb_to_hsv(rgb_color)
        h, s, v = hsv
        
        # Shift hue (h is in range 0-1, so convert degrees to fraction)
        h_shifted = (h + hue_shift_degrees / 360.0) % 1.0
        
        # Convert back to RGB
        return mcolors.hsv_to_rgb((h_shifted, s, v))
    except:
        return rgb_color


def map_trewartha_to_color(code: str) -> str:
    # Hardcoded mapping by full 4-letter code; fallback to gray if unknown
    if not isinstance(code, str) or len(code) < 4:
        return "#888888"
    return TREWARTHA_CODE_COLORS.get(code, "#888888")


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
    
    # Get all climate zones present in data
    climate_zones = sorted(df_filtered['trewartha'].astype(str).str[0].unique())
    print(f"Found climate zones: {climate_zones}")
    
    image_paths = []
    
    # Generate images for each year and each climate zone
    for year in year_range:
        print(f"\nProcessing year {year}...")
        df_year = df_filtered[df_filtered['year'] == year]
        
        if len(df_year) == 0:
            print(f'No data for year {year}, skipping...')
            continue
            
        print(f"Rows for year {year}: {len(df_year)}")
        
        # Create separate map for each climate zone
        for zone in climate_zones:
            # Remove the CLIMATE_ZONE_COLORS check since it's no longer needed
            df_zone = df_year[df_year['trewartha'].astype(str).str[0] == zone]
            if len(df_zone) == 0:
                continue
                
            print(f"  Processing climate zone {zone}: {len(df_zone)} points")
            
            # Optionally reduce point count for faster rendering
            if len(df_zone) > 50000:
                print(f'    Large number of points, sampling 50k for plotting...')
                df_zone = df_zone.sample(n=50000, random_state=1)

            # Generate output path
            out_path = output_dir / f"trewartha_zone_{zone}_{year}.png"
            
            # Create custom caption
            zone_caption = f"Trewartha Climate Zone {zone} - {year}"
            if args.caption:
                zone_caption = f"{args.caption} - Zone {zone}"
            
            # Create the plot
            if HAS_CARTOPY:
                print(f'    Using cartopy for zone {zone} map rendering')
                plot_with_cartopy(df_zone, year, str(out_path), zone_caption)
            else:
                print(f'    Cartopy not available, using simple scatter for zone {zone}')
                plot_simple(df_zone, year, str(out_path), zone_caption)

            print(f'    Wrote zone {zone} map image to {out_path}')
            image_paths.append(str(out_path))
    
    # Create animation if requested (will include all zones)
    if args.animation and image_paths:
        animation_path = output_dir / f"trewartha_zones_animation_{args.start_year}_{args.end_year}.gif"
        print(f"\nCreating animation: {animation_path}")
        
        if create_animation(image_paths, str(animation_path), args.animation_duration):
            print(f"Animation created successfully: {animation_path}")
        else:
            print("Failed to create animation")
    
    print(f"\nCompleted! Generated {len(image_paths)} images in {output_dir}")

if __name__ == '__main__':
    main()
