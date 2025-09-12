import argparse
from app.climate.service import ClimateService

def main():
    parser = argparse.ArgumentParser(description="Climate classification CLI")
    parser.add_argument("place", help="Place name")
    parser.add_argument("start_year", type=int)
    parser.add_argument("end_year", type=int)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()

    service = ClimateService()
    resp = service.fetch(args.place, args.start_year, args.end_year, aggregate=args.aggregate)
    if args.aggregate and resp.aggregate:
        agg = resp.aggregate
        print(f"Aggregate {agg.place} {agg.start_year}-{agg.end_year}: mean_temp={agg.mean_temp_c}C total_precip={agg.total_precip_mm}mm dominant={agg.dominant_classification}")
    for r in resp.records:
        print(f"{r.year}: {r.avg_temp_c}C {r.precipitation_mm}mm {r.classification}")

if __name__ == "__main__":
    main()
