from __future__ import annotations

def parse_years(spec: str) -> list[int]:
    """Parse a year specification string into a sorted unique list of years.

    Supported formats:
      2024                -> [2024]
      2000-2005           -> [2000,2001,2002,2003,2004,2005]
      1998,2000-2002,2005 -> [1998,2000,2001,2002,2005]

    Whitespace is ignored. Raises ValueError on malformed input.
    """
    if not spec or not isinstance(spec, str):
        raise ValueError("Year spec must be a non-empty string")
    years: set[int] = set()
    parts = [p.strip() for p in spec.split(',') if p.strip()]
    for part in parts:
        if '-' in part:
            segs = part.split('-')
            if len(segs) != 2:
                raise ValueError(f"Invalid range segment: {part}")
            start_s, end_s = segs
            if not (start_s.isdigit() and end_s.isdigit()):
                raise ValueError(f"Non-numeric year in range: {part}")
            start = int(start_s); end = int(end_s)
            if end < start:
                raise ValueError(f"Range start > end: {part}")
            if start < 1800 or end > 2100:
                raise ValueError(f"Year out of reasonable bounds: {part}")
            for y in range(start, end+1):
                years.add(y)
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid year token: {part}")
            y = int(part)
            if y < 1800 or y > 2100:
                raise ValueError(f"Year out of reasonable bounds: {y}")
            years.add(y)
    if not years:
        raise ValueError("No years parsed")
    return sorted(years)
