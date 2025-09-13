"""Command line interface for climate classification (currently stale).

WHAT: Intended to provide a CLI wrapper around `ClimateService` for
fetching yearly or aggregated climate data.

STATUS / ISSUE: The code calls `ClimateService.fetch(...)` which no longer
exists in the service implementation (API shifted to
`get_aggregated_climate_data` / `get_yearly_climate_data`). This script is
therefore non-functional and needs refactor or removal.

WHY HERE: Scripts folder collects operational utilities (model building,
CLI). No external APIs beyond those used indirectly via the service
(Nominatim + local model files).
"""

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
    # DEAD CODE: Original fetch interface removed. Placeholder logic below
    # demonstrates how a refactored CLI might look; keeping failure to
    # highlight required maintenance instead of silently drifting.
    print("ERROR: 'ClimateService.fetch' no longer exists. Update CLI to use new service methods.")
    # Example future adaptation (pseudo):
    # if args.aggregate:
    #     loc, temps, precips, classification, dist = service.get_aggregated_climate_data(args.place, list(range(args.start_year, args.end_year+1)))
    # else:
    #     loc, year_map, dist = service.get_yearly_climate_data(args.place, list(range(args.start_year, args.end_year+1)))
    # print(...)

if __name__ == "__main__":
    main()
