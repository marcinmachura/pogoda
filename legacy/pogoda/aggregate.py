from __future__ import annotations
from typing import Iterable, List, Dict

def aggregate_monthly(records: Iterable[Dict[str, List[float]]]) -> Dict[str, List[float]]:
    """Aggregate multiple yearly records into mean monthly series.

    Each record must have keys 'T2M' and 'PRECTOT' with length-12 lists.
    Returns dict with same keys; precipitation is mean of annual monthly totals.
    """
    temps_acc = [0.0]*12
    precip_acc = [0.0]*12
    n = 0
    for rec in records:
        t = rec['T2M']; p = rec['PRECTOT']
        if len(t) != 12 or len(p) !=12:
            raise ValueError("All records must have 12 monthly values")
        for i in range(12):
            temps_acc[i] += t[i]
            precip_acc[i] += p[i]
        n += 1
    if n == 0:
        raise ValueError("No records to aggregate")
    return {
        'T2M': [v / n for v in temps_acc],
        'PRECTOT': [v / n for v in precip_acc]
    }
