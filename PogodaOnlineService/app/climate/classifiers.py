"""Simplified Köppen and Trewartha climate classification algorithms.

WHAT: Implements pragmatic, testable versions of Köppen (`classify_koppen`)
and Trewartha (`classify_trewartha`) classification returning a code plus
details dictionary. Includes custom `ClassificationError` for invalid
inputs.

WHY HERE: Encapsulated within climate domain to keep scientific rules and
threshold logic separate from service orchestration and API concerns.
External APIs: None – pure computation from monthly temperature &
precipitation sequences.
"""

from __future__ import annotations
from typing import List, Dict, Tuple

__all__ = [
    "ClassificationError",
    "classify_trewartha",
    "classify_koppen"
]


class ClassificationError(ValueError):
    pass

def classify_trewartha(temps_c: List[float], precip_mm: List[float], latitude: float) -> Tuple[str, Dict[str, float]]:
    """Classify climate using a simplified Trewartha system.

     Implementation notes
     --------------------
     1. Dry (B) climates determined first using Köppen-like dryness threshold.
     2. Canonical groups after dryness check:
         - A: All 12 months >= 18°C (true tropical)
         - C: Subtropical (m10 >= 8) (at least 8 months >=10°C but not all >=18°C)
         - D: Temperate/Oceanic (4 <= m10 <= 7)
         - E: Boreal/Subpolar (1 <= m10 <= 3)
         - F: Polar (m10 == 0)
    3. Four-letter code for non-arid (non-B) climates:
        [Group][Precip][Summer][Thermal]
        - Precip: s (dry summer), w (dry winter), f (no pronounced dry season)
        - Summer: a (hot, warmest ≥22°C), b (warm, warmest <22°C but ≥4 months ≥10°C), c (cool/short summer: 1–3 months ≥10°C)
        - Thermal (Universal Thermal Scale, based on ANNUAL mean temperature, Wikipedia ranges):
            i: ≥35°C (severely hot)
            h: 28–34.9°C (very hot)
            a: 22.2–27.9°C (hot)
            b: 18–22.1°C (warm)
            l: 10–17.9°C (mild)
            k: 0.1–9.9°C (cool)
            o: −9.9–0°C (cold)
            c: −24.9––10°C (very cold)
            d: −39.9––25°C (severely cold)
            e: ≤−40°C (excessively cold)
      (Note: Previous implementation used a winter severity letter; this has been replaced for conformity.)
    4. Arid B climates retain 3-letter form (BW/BS + h/k) for familiarity.
    5. Seasonality letters (f, s, w) for A, C, D if not dry: based on ratio comparisons.
    6. B climates subdivided into BW/BS (desert/steppe) and temperature qualifier h/k (>=18°C mean).
    7. For polar (E/F here): still produce four-letter code with thermal scale.
    8. This pragmatic version may be refined later.
    """
    if len(temps_c) != 12 or len(precip_mm) != 12:
        raise ClassificationError("Need 12 monthly temperature and precipitation values")

    annual_mean_temp = sum(temps_c)/12.0
    annual_precip = sum(precip_mm)
    warmest = max(temps_c)
    coldest = min(temps_c)
    m10 = sum(1 for t in temps_c if t >= 10.0)

    # Hemisphere seasons (align with Köppen function choices)
    if latitude >= 0:
        summer_indices = [3,4,5,6,7,8]  # Apr-Sep
        winter_indices = [9,10,11,0,1,2]
    else:
        summer_indices = [9,10,11,0,1,2]
        winter_indices = [3,4,5,6,7,8]
    precip_summer = sum(precip_mm[i] for i in summer_indices)
    precip_winter = sum(precip_mm[i] for i in winter_indices)
    summer_share = precip_summer/annual_precip if annual_precip>0 else 0
    winter_share = precip_winter/annual_precip if annual_precip>0 else 0

    # Dryness threshold (same formula used in simplified Köppen implementation)
    if summer_share >= 0.70:
        R = 2*annual_mean_temp + 28
    elif winter_share >= 0.70:
        R = 2*annual_mean_temp
    else:
        R = 2*annual_mean_temp + 14

    details = dict(
        annual_mean_temp=annual_mean_temp,
        annual_precip=annual_precip,
        warmest=warmest,
        coldest=coldest,
        months_ge_10=m10,
        precip_summer=precip_summer,
        precip_winter=precip_winter,
        summer_share=summer_share,
        winter_share=winter_share,
        dryness_threshold_R=R,
    )

    # Dry group overrides others
    if annual_precip < R:
        if annual_precip < 0.5 * R:
            sub1 = 'W'
        else:
            sub1 = 'S'
        temp_qual = 'h' if annual_mean_temp >= 18.0 else 'k'
        code = 'B' + sub1 + temp_qual
        details['group'] = 'B'
        details['sub1'] = sub1
        details['temp_qual'] = temp_qual
        details['four_letter'] = False
        return code, details

    # Non-dry classification by canonical rules
    if all(t >= 18.0 for t in temps_c):
        group = 'A'
    elif m10 >= 8:
        group = 'C'
    elif 4 <= m10 <= 7:
        group = 'D'
    elif 1 <= m10 <= 3:
        group = 'E'
    else:
        group = 'F'

    def thermal_letter(mean_t: float) -> str:
        # Descending thresholds; ranges per Universal Thermal Scale
        if mean_t >= 35.0:
            return 'i'
        if mean_t >= 28.0:
            return 'h'
        if mean_t >= 22.2:
            return 'a'
        if mean_t >= 18.0:
            return 'b'
        if mean_t >= 10.0:
            return 'l'
        if mean_t >= 0.1:
            return 'k'
        if mean_t >= -9.9:  # -9.9 to 0.0
            return 'o'
        if mean_t >= -24.9:
            return 'c'
        if mean_t >= -39.9:
            return 'd'
        return 'e'

    if group == 'F':  # Polar (retain logic but new thermal letter)
        subtype = 'T' if warmest >= 0.0 and warmest < 10.0 else ('F' if warmest < 0.0 else 'T')
        second = 'f'
        summer_letter = 'c'
        t_letter = thermal_letter(annual_mean_temp)
        code = group + second + summer_letter + t_letter
        details['group'] = group
        details['subtype'] = subtype
        details['second'] = second
        details['third'] = summer_letter
        details['thermal_scale'] = t_letter
        details['four_letter'] = True
        return code, details

    # Precipitation seasonality second letter using monthly ratio criteria (Mediterranean / monsoonal detection)
    # 's': driest summer month < 40 mm AND < 1/3 of wettest winter month
    # 'w': driest winter month < (wettest summer month / 10)
    # else 'f'
    summer_months = [precip_mm[i] for i in summer_indices]
    winter_months = [precip_mm[i] for i in winter_indices]
    driest_summer = min(summer_months) if summer_months else 0
    driest_winter = min(winter_months) if winter_months else 0
    wettest_winter = max(winter_months) if winter_months else 0
    wettest_summer = max(summer_months) if summer_months else 0
    if driest_summer < 40 and wettest_winter and driest_summer < (wettest_winter / 3.0):
        second = 's'
    elif wettest_summer and driest_winter < (wettest_summer / 10.0):
        second = 'w'
    else:
        second = 'f'

    # Temperature qualifier: a = warmest >= 22, b = warmest < 22 but at least 4 months >=10, c/d rarely used here; keep simple
    if group in ('C','D','E','A'):
        if warmest >= 22.0:
            third = 'a'
        elif m10 >= 4:
            third = 'b'
        else:
            third = 'c'
    else:
        third = ''

    # Universal thermal scale letter based on annual mean temperature
    t_letter = thermal_letter(annual_mean_temp)

    if third:  # non-arid group
        code = group + second + third + t_letter
        details['four_letter'] = True
        details['thermal_scale'] = t_letter
    else:  # pathological fallback
        code = group + second + t_letter
        details['four_letter'] = False
        details['thermal_scale'] = t_letter
    details['group'] = group
    details['second'] = second
    details['third'] = third
    return code, details





def classify_koppen(temps_c: List[float], precip_mm: List[float], latitude: float) -> Tuple[str, Dict[str, float]]:
    """Classify climate using simplified Köppen system.

    Notes
    -----
    - Uses -3°C isotherm between C and D (common modern variant); adjust if needed.
    - Requires 12 monthly mean temps and 12 monthly precip totals.
    - Simplified tertiary letters for temperate/continental groups.
    """
    if len(temps_c) != 12 or len(precip_mm) != 12:
        raise ClassificationError("Need 12 monthly temperature and precipitation values")

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
