#!/usr/bin/env python3
"""Test script for the climate API."""

import requests
import json


def test_climate_api():
    """Test the climate API endpoints."""
    base_url = "http://127.0.0.1:8000"
    
    # Test 1: Yearly endpoint (returns classifications per year)
    print("Testing POST /api/v1/climate/yearly")
    yearly_data = {
        "city": "London",
        "years": [2020, 2021, 2022]
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/climate/yearly", json=yearly_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS! Yearly Response:")
            print(f"  Location: {data['location']['city']} ({data['location']['latitude']}, {data['location']['longitude']})")
            print(f"  Years: {data['start_year']}-{data['end_year']}")
            print(f"  Distance to climate station: {data.get('distance_km', 'N/A')} km")
            
            # Show classification details for each year
            if data.get('yearly_data'):
                print("  Yearly Classifications:")
                for year, classification in data['yearly_data'].items():
                    print(f"    {year}: {classification['koppen_code']} ({classification['koppen_name']})")
                    print(f"           {classification['trewartha_code']} ({classification['trewartha_name']})")
        else:
            print(f"ERROR: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to server. Make sure it's running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Aggregated endpoint (returns monthly averages and classification)
    print("Testing POST /api/v1/climate/aggregated")
    agg_data = {
        "city": "Paris",
        "years": [2020, 2021, 2022]
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/climate/aggregated", json=agg_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Aggregated Response:")
            print(f"  Location: {data['location']['city']} ({data['location']['latitude']}, {data['location']['longitude']})")
            print(f"  Years: {data['start_year']}-{data['end_year']}")
            print(f"  Distance to climate station: {data.get('distance_km', 'N/A')} km")
            
            if data.get('climate_data'):
                climate = data['climate_data']
                classification = climate['classification']
                print(f"  Climate Data:")
                print(f"    Classification: {classification['koppen_code']} ({classification['koppen_name']})")
                print(f"    Trewartha: {classification['trewartha_code']} ({classification['trewartha_name']})")
                print(f"    Monthly temps: {[round(t, 1) for t in climate['avg_monthly_temps'][:3]]}C... (first 3 months)")
                print(f"    Monthly precip: {[round(p, 1) for p in climate['avg_monthly_precip'][:3]]}mm... (first 3 months)")
        else:
            print(f"ERROR: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to server. Make sure it's running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    print("Climate API Test Suite")
    print("="*50)
    test_climate_api()
    print("\nFor manual browser testing:")
    print("1. Start the server: python app/main.py")
    print("2. Go to: http://127.0.0.1:8000/docs")
    print("3. Use the interactive API documentation (Swagger UI)")
    print("4. Or use a tool like Postman with the JSON payloads shown above")