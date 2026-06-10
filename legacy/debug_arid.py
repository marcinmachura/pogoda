#!/usr/bin/env python3
"""Debug arid classification for desert cities."""

from pogoda.geocode import geocode_city
from pogoda.power import fetch_power_monthly
from pogoda.koppen import classify_koppen
from pogoda.trewartha import classify_trewartha

def debug_city(city_name: str, year: int = 2020):
    print(f"\n=== Debugging {city_name} ({year}) ===")
    
    # Get coordinates
    location = geocode_city(city_name)
    lat, lon = location.latitude, location.longitude
    print(f"Coordinates: ({lat:.4f}, {lon:.4f})")
    
    # Fetch data
    data = fetch_power_monthly(lat, lon, year)
    temps = data['T2M']
    precip = data['PRECTOT']
    
    print(f"Annual mean temp: {sum(temps)/12:.1f}°C")
    print(f"Annual precip: {sum(precip):.1f}mm")
    print(f"Monthly temps: {[round(t,1) for t in temps]}")
    print(f"Monthly precip: {[round(p,1) for p in precip]}")
    
    # Köppen analysis
    koppen_code, koppen_details = classify_koppen(temps, precip, lat)
    print(f"\nKöppen: {koppen_code}")
    print(f"  Dryness threshold R: {koppen_details['dryness_threshold_R']:.1f}mm")
    print(f"  Annual precip: {koppen_details['annual_precip']:.1f}mm")
    print(f"  Is arid (P < R)?: {koppen_details['annual_precip'] < koppen_details['dryness_threshold_R']}")
    print(f"  Summer share: {koppen_details['summer_share']:.2f}")
    print(f"  Winter share: {koppen_details['winter_share']:.2f}")
    
    # Trewartha analysis
    trewartha_code, trewartha_details = classify_trewartha(temps, precip, lat)
    print(f"\nTrewartha: {trewartha_code}")
    print(f"  Dryness threshold R: {trewartha_details['dryness_threshold_R']:.1f}mm")
    print(f"  Is arid (P < R)?: {trewartha_details['annual_precip'] < trewartha_details['dryness_threshold_R']}")

if __name__ == "__main__":
    debug_city("cairo,egypt")
    debug_city("dubai,uae") 
    debug_city("honolulu,hawaii")
