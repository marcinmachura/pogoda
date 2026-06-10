from __future__ import annotations
import argparse
import json
from .geocode import geocode_city
from .power import fetch_power_monthly, PowerAPIError
from .koppen import classify_koppen, KoppenClassificationError
from .trewartha import classify_trewartha, TrewarthaClassificationError
from .year_range import parse_years
from .aggregate import aggregate_monthly
from .cache import load_cached, store_cache
try:
    from tqdm import tqdm
except ImportError:  # graceful fallback
    tqdm = None

try:
    import kgcpy
    KGCPY_AVAILABLE = True
except ImportError:
    KGCPY_AVAILABLE = False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Köppen climate classifier using NASA POWER")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("classify", help="Classify a city's climate for a year")
    c.add_argument("city", type=str, help="City name, optionally with country")
    c.add_argument("--year", type=str, default="2024", help="Year or range/list, e.g. 2024 or 2000-2024 or 1990,1995,2000-2002")
    c.add_argument("--scheme", choices=["koppen","trewartha","both"], default="koppen", help="Classification scheme")
    c.add_argument("--multi-mode", choices=["aggregate","per-year","both"], default="aggregate", help="How to handle multi-year ranges (default: aggregate)")
    c.add_argument("--json", action="store_true", help="Output JSON only")
    c.add_argument("--cache-dir", type=str, default="cache", help="Directory for cached yearly data")
    c.add_argument("--no-cache", action="store_true", help="Disable cache read/write")
    c.add_argument("--force-refresh", action="store_true", help="Ignore existing cache and re-download")
    c.add_argument("--show-details", "-d", action="store_true", help="Print full classifier detail objects in text mode")
    return p


def cmd_classify(args):
    loc = geocode_city(args.city)
    years = parse_years(args.year)
    multi = len(years) > 1
    results = []
    raw_year_data = []  # store fetched raw monthly data for possible aggregation
    
    # Get kgcpy reference classification if available
    kgcpy_result = None
    if KGCPY_AVAILABLE:
        try:
            kgcpy_result = kgcpy.lookupCZ(loc.latitude, loc.longitude)
        except Exception as e:
            if not args.json:
                print(f"Warning: kgcpy lookup failed: {e}")
    
    iterable = years
    if tqdm and len(years) > 1 and not args.json:
        iterable = tqdm(years, desc="Fetching NASA POWER", unit="yr")
    for yr in iterable:
        year_data = None
        if not args.no_cache and not args.force_refresh:
            year_data = load_cached(loc.latitude, loc.longitude, yr, args.cache_dir)
        if year_data is None:
            year_data = fetch_power_monthly(loc.latitude, loc.longitude, yr)
            if not args.no_cache:
                store_cache(loc.latitude, loc.longitude, yr, args.cache_dir, year_data)
        record = {"year": yr}
        if args.scheme in ("koppen","both"):
            k_code, k_det = classify_koppen(year_data['T2M'], year_data['PRECTOT'], loc.latitude)
            record['koppen_code'] = k_code
            record['koppen_details'] = k_det
        if args.scheme in ("trewartha","both"):
            t_code, t_det = classify_trewartha(year_data['T2M'], year_data['PRECTOT'], loc.latitude)
            record['trewartha_code'] = t_code
            record['trewartha_details'] = t_det
        record['temps_c'] = year_data['T2M']
        record['precip_mm'] = year_data['PRECTOT']
        results.append(record)
        raw_year_data.append(year_data)

    aggregate_record = None
    if multi and args.multi_mode in ("aggregate","both"):
        agg = aggregate_monthly(raw_year_data)
        agg_rec = {"years": years}
        if args.scheme in ("koppen","both"):
            k_code, k_det = classify_koppen(agg['T2M'], agg['PRECTOT'], loc.latitude)
            agg_rec['koppen_code'] = k_code
            agg_rec['koppen_details'] = k_det
        if args.scheme in ("trewartha","both"):
            t_code, t_det = classify_trewartha(agg['T2M'], agg['PRECTOT'], loc.latitude)
            agg_rec['trewartha_code'] = t_code
            agg_rec['trewartha_details'] = t_det
        agg_rec['temps_c'] = agg['T2M']
        agg_rec['precip_mm'] = agg['PRECTOT']
        aggregate_record = agg_rec

    if args.json:
        out = {
            "input_city": args.city,
            "resolved_name": loc.name,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "years": years,
            "results": results,
            "aggregate": aggregate_record,
            "scheme": args.scheme,
            "source": "NASA POWER",
            "source_url": "https://power.larc.nasa.gov/",
            "kgcpy_reference": kgcpy_result
        }
        print(json.dumps(out, indent=2))
    else:
        header = f"City: {args.city} -> {loc.name}\nCoords: ({loc.latitude:.4f}, {loc.longitude:.4f})"
        if kgcpy_result:
            header += f"\nkgcpy reference: {kgcpy_result}"
        print(header)
        if aggregate_record:
            years_str = f"{years[0]}-{years[-1]}" if years[0] != years[-1] else f"{years[0]}"
            line = f"Aggregate {years_str}:"
            if 'koppen_code' in aggregate_record:
                line += f" Köppen={aggregate_record['koppen_code']}"
            if 'trewartha_code' in aggregate_record:
                line += f" Trewartha={aggregate_record['trewartha_code']}"
            ref = aggregate_record.get('koppen_details') or aggregate_record.get('trewartha_details')
            if ref:
                line += f" (Tmean={ref['annual_mean_temp']:.1f}°C P={ref['annual_precip']:.0f}mm)"
            print(line)
            if args.show_details:
                if 'koppen_details' in aggregate_record:
                    print("  Köppen details:")
                    print(json.dumps(aggregate_record['koppen_details'], indent=2, sort_keys=True))
                if 'trewartha_details' in aggregate_record:
                    print("  Trewartha details:")
                    print(json.dumps(aggregate_record['trewartha_details'], indent=2, sort_keys=True))
        if not aggregate_record or args.multi_mode in ("per-year","both"):
            for rec in results:
                line = f"{rec['year']}:"
                if 'koppen_code' in rec:
                    line += f" Köppen={rec['koppen_code']}"
                if 'trewartha_code' in rec:
                    line += f" Trewartha={rec['trewartha_code']}"
                if 'koppen_details' in rec:
                    am = rec['koppen_details']['annual_mean_temp']
                    ap = rec['koppen_details']['annual_precip']
                    line += f" (Tmean={am:.1f}°C P={ap:.0f}mm)"
                elif 'trewartha_details' in rec:
                    am = rec['trewartha_details']['annual_mean_temp']
                    ap = rec['trewartha_details']['annual_precip']
                    line += f" (Tmean={am:.1f}°C P={ap:.0f}mm)"
                print(line)
                if args.show_details:
                    if 'koppen_details' in rec:
                        print("  Köppen details:")
                        print(json.dumps(rec['koppen_details'], indent=2, sort_keys=True))
                    if 'trewartha_details' in rec:
                        print("  Trewartha details:")
                        print(json.dumps(rec['trewartha_details'], indent=2, sort_keys=True))


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == 'classify':
            cmd_classify(args)
    except (PowerAPIError, KoppenClassificationError, TrewarthaClassificationError, ValueError) as e:
        print(f"Error: {e}")
        raise SystemExit(1)

if __name__ == "__main__":  # pragma: no cover
    main()
