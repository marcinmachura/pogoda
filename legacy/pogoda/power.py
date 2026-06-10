from __future__ import annotations
import requests
from datetime import datetime
from typing import Dict, List

BASE_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

class PowerAPIError(RuntimeError):
    pass

def fetch_power_monthly(lat: float, lon: float, year: int) -> Dict[str, List[float]]:
    """Fetch monthly temperature and precipitation from NASA POWER.

    Parameters
    ----------
    lat, lon : float
        Coordinates.
    year : int
        Calendar year.

    Returns
    -------
    dict with keys: 'T2M' (list[12] monthly mean temp °C), 'PRECTOT' (list[12] monthly precip mm total)

    Raises
    ------
    PowerAPIError on network or data issues.
    """
    params = {
        "parameters": "T2M,PRECTOTCORR",
        "community": "RE",
        "latitude": lat,
        "longitude": lon,
        "start": year,
        "end": year,
        "format": "JSON"
    }
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
    except requests.RequestException as e:
        raise PowerAPIError(f"Request failed: {e}") from e
    if r.status_code != 200:
        raise PowerAPIError(f"Bad status code {r.status_code}: {r.text[:200]}")
    data = r.json()

    temps: List[float]
    precs: List[float]

    # Newer API variant may expose top-level 'parameters' & 'times'. Original used properties.parameter
    try:
        if 'properties' in data and isinstance(data['properties'], dict) and 'parameter' in data['properties']:
            params_data = data['properties']['parameter']
            t_values = params_data['T2M']
            p_values = params_data.get('PRECTOTCORR')  # mm/day means
            if p_values is None:
                raise PowerAPIError("PRECTOTCORR not present in properties.parameter")
            if isinstance(t_values, dict):
                # Filter out annual key e.g. '202413'
                month_items = {k: v for k, v in t_values.items() if k.startswith(str(year)) and not k.endswith('13')}
                ordered_keys = sorted(month_items.keys())
                if len(ordered_keys) != 12:
                    raise PowerAPIError(f"Expected 12 monthly temperature keys, got {len(ordered_keys)}")
                from calendar import monthrange
                temps = [round(float(month_items[k]), 3) for k in ordered_keys]
                precs = []
                for k in ordered_keys:
                    month = int(k[-2:])
                    days = monthrange(year, month)[1]
                    daily_mm = float(p_values[k])
                    precs.append(round(daily_mm * days, 3))
            elif isinstance(t_values, list):  # paired with explicit month ordering? unlikely but handle
                if len(t_values) != 12:
                    raise PowerAPIError("Expected 12 monthly temperature values in list form")
                temps = [round(float(v), 3) for v in t_values]
                from calendar import monthrange
                precs = [round(float(v) * monthrange(year, i+1)[1], 3) for i, v in enumerate(p_values)]
            else:
                raise PowerAPIError("Unrecognized temperature value container type")
        elif 'parameters' in data and 'times' in data:
            times = data['times']
            params_block = data['parameters']
            if 'T2M' not in params_block or 'PRECTOTCORR' not in params_block:
                raise PowerAPIError("Missing T2M or PRECTOTCORR in parameters block")
            t_series = params_block['T2M']
            p_series = params_block['PRECTOTCORR']
            if not (isinstance(t_series, list) and isinstance(p_series, list)):
                raise PowerAPIError("Expected list series for T2M and PRECTOTCORR in new format")
            if len(t_series) != 12 or len(p_series) != 12:
                raise PowerAPIError(f"Expected 12 months; got {len(t_series)} temps, {len(p_series)} precip")
            # Optionally validate times entries belong to requested year
            temps = [round(float(v), 3) for v in t_series]
            from calendar import monthrange
            precs = [round(float(v) * monthrange(year, i+1)[1], 3) for i, v in enumerate(p_series)]
        else:
            raise PowerAPIError(f"Unexpected JSON structure: {list(data.keys())}")
    except KeyError as e:
        raise PowerAPIError(f"Key error parsing POWER response: {e}") from e

    if len(temps) != 12 or len(precs) != 12:
        raise PowerAPIError(f"Expected 12 months; got {len(temps)} temps, {len(precs)} precip")

    return {"T2M": temps, "PRECTOT": precs}
