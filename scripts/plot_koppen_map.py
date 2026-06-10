"""Plot Koppen classifications for a given year on a map of Europe.

Reads CSV produced by the F# program (format: Lat,Lon,year,koppen,trewartha).
Defaults to /tmp/climate_classifications.csv and year 2018.

The script will try to use cartopy for a proper map projection and coastlines.
If cartopy is not available it will fall back to a simple lon/lat scatter plot.

Usage:
    python plot_koppen_map.py --csv /tmp/climate_classifications.csv --year 2018 --out /tmp/koppen_2018.png

Requirements (recommended):
    pip install pandas matplotlib cartopy

"""
import argparse
import sys
from collections import OrderedDict

import pandas as pd
import matplotlib.pyplot as plt

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


def plot_with_cartopy(df, year, out_path):
    fig = plt.figure(figsize=(12, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-25, 45, 30, 72], crs=ccrs.PlateCarree())  # Europe-ish extent
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"))
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linestyle=':')
    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f0f0f0")
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#a6cee3")

    # map colors
    colors = df['koppen'].apply(map_koppen_to_color)
    sc = ax.scatter(df['lon'], df['lat'], c=colors.tolist(), s=8, alpha=0.8, transform=ccrs.PlateCarree())

    # build legend for the most frequent classes
    top_codes = df['koppen'].value_counts().head(12).index.tolist()
    build_legend(ax, top_codes)

    ax.set_title(f"Koppen classification, {year}")
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)


def plot_simple(df, year, out_path):
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(-25, 45)
    ax.set_ylim(30, 72)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title(f"Koppen classification (simple), {year}")
    colors = df['koppen'].apply(map_koppen_to_color)
    ax.scatter(df['lon'], df['lat'], c=colors.tolist(), s=6, alpha=0.8)
    top_codes = df['koppen'].value_counts().head(12).index.tolist()
    build_legend(ax, top_codes)
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', default='/tmp/climate_classifications.csv', help='path to CSV')
    p.add_argument('--year', type=int, default=2018)
    p.add_argument('--out', default=None, help='output image path (default: koppen_<year>.png in current dir)')
    args = p.parse_args()
    if args.out is None:
        args.out = f"koppen_{args.year}.png"

    print(f"Reading {args.csv} ...")
    df = pd.read_csv(args.csv, usecols=['Lat','Lon','year','koppen'], dtype={'Lat': float, 'Lon': float, 'year': int, 'koppen': str})
    df = df.rename(columns={'Lat': 'lat', 'Lon': 'lon'})
    df = df[df['year'] == args.year]
    print(f"Rows for year {args.year}: {len(df)}")
    if len(df) == 0:
        print('No data for that year')
        sys.exit(1)

    # Optionally reduce point count for faster rendering (sample if huge)
    if len(df) > 200000:
        print('Large number of points, sampling 200k for plotting...')
        df = df.sample(n=200000, random_state=1)

    if HAS_CARTOPY:
        print('Using cartopy for map rendering')
        plot_with_cartopy(df, args.year, args.out)
    else:
        print('Cartopy not available, using simple scatter')
        plot_simple(df, args.year, args.out)

    print(f'Wrote map image to {args.out}')


if __name__ == '__main__':
    main()
