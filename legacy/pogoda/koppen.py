from __future__ import annotations
from typing import List, Dict, Tuple

class KoppenClassificationError(ValueError):
    pass

def classify_koppen(temps_c: List[float], precip_mm: List[float], latitude: float) -> Tuple[str, Dict[str, float]]:
    """Classify climate using simplified Köppen system.

    Notes
    -----
    - Uses -3°C isotherm between C and D (common modern variant); adjust if needed.
    - Requires 12 monthly mean temps and 12 monthly precip totals.
    - Simplified tertiary letters for temperate/continental groups.
    """
    if len(temps_c) != 12 or len(precip_mm) != 12:
        raise KoppenClassificationError("Need 12 monthly temperature and precipitation values")

    # Basic derived metrics
    annual_mean_temp = sum(temps_c) / 12.0
    annual_precip = sum(precip_mm)
    warmest = max(temps_c)
    coldest = min(temps_c)
    months_ge_10 = sum(1 for t in temps_c if t >= 10.0)

    # Hemisphere aware: define summer/winter half-year
    # Northern: Apr-Sep as summer (months 4-9); Southern: Oct-Mar (months 10-3)
    if latitude >= 0:
        summer_indices = [3,4,5,6,7,8]  # 0-based for Apr-Sep
        winter_indices = [9,10,11,0,1,2]
    else:
        summer_indices = [9,10,11,0,1,2]
        winter_indices = [3,4,5,6,7,8]
    precip_summer = sum(precip_mm[i] for i in summer_indices)
    precip_winter = sum(precip_mm[i] for i in winter_indices)

    summer_share = precip_summer / annual_precip if annual_precip > 0 else 0
    winter_share = precip_winter / annual_precip if annual_precip > 0 else 0

    # Dryness threshold (Köppen B) R
    if summer_share >= 0.70:
        R = 2 * annual_mean_temp + 28
    elif winter_share >= 0.70:
        R = 2 * annual_mean_temp
    else:
        R = 2 * annual_mean_temp + 14

    details = dict(
        annual_mean_temp=annual_mean_temp,
        annual_precip=annual_precip,
        warmest=warmest,
        coldest=coldest,
        months_ge_10=months_ge_10,
        precip_summer=precip_summer,
        precip_winter=precip_winter,
        summer_share=summer_share,
        winter_share=winter_share,
        dryness_threshold_R=R,
    )

    # Main group determination (order matters: arid first)
    if annual_precip < R:
        main = 'B'
    elif min(temps_c) >= 18.0:
        main = 'A'
    elif warmest < 10.0:
        main = 'E'
    elif coldest > -3.0:
        main = 'C'
    else:
        main = 'D'

    # Special polar subtypes
    if main == 'E':
        subtype = 'T' if warmest > 0.0 else 'F'
        code = main + subtype
        details['group'] = main
        details['subtype'] = subtype
        return code, details

    # Arid subdivisions (B)
    if main == 'B':
        if annual_precip < 0.5 * R:
            sub1 = 'W'  # desert
        else:
            sub1 = 'S'  # steppe
        # Temperature qualifier
        if annual_mean_temp >= 18.0:
            sub2 = 'h'
        else:
            sub2 = 'k'
        code = main + sub1 + sub2
        details['group'] = main
        details['sub1'] = sub1
        details['sub2'] = sub2
        return code, details

    # Seasonality second letter for A, C, D
    # Monthly ratio criteria (classical):
    # 's': driest summer month < 40 mm AND < 1/3 of wettest winter month
    # 'w': driest winter month < (wettest summer month / 10)
    # else 'f'
    summer_months = [precip_mm[i] for i in summer_indices]
    winter_months = [precip_mm[i] for i in winter_indices]
    driest_summer = min(summer_months) if summer_months else 0
    driest_winter = min(winter_months) if winter_months else 0
    wettest_winter = max(winter_months) if winter_months else 0
    wettest_summer = max(summer_months) if summer_months else 0
    if driest_summer < 40 and wettest_winter and driest_summer < (wettest_winter/3.0):
        second = 's'
    elif wettest_summer and driest_winter < (wettest_summer/10.0):
        second = 'w'
    else:
        second = 'f'

    # Temperature third letter for C/D
    if main in ('C','D'):
        if warmest >= 22.0 and months_ge_10 >= 4:
            third = 'a'
        elif months_ge_10 >= 4 and warmest < 22.0:
            third = 'b'
        elif months_ge_10 >= 1:
            third = 'c'
        else:
            third = 'd'  # very cold winters
    else:
        third = ''

    # Tropical sub letters (A)
    if main == 'A':
        # Af: no dry month (all months >= 60 mm) - simplified using 60 mm absolute
        if all(p >= 60 for p in precip_mm):
            second = 'f'
        else:
            # Am vs Aw: If short dry season but not pronounced vs strong winter dryness
            # Simplified: choose 'w' if any winter month < 60 and precip_winter < precip_summer
            if any(precip_mm[i] < 60 for i in winter_indices) and precip_winter < precip_summer:
                second = 'w'
            else:
                second = 'm'
        code = main + second
        details['group'] = main
        details['second'] = second
        return code, details

    code = main + second + third
    details['group'] = main
    details['second'] = second
    details['third'] = third
    return code, details
