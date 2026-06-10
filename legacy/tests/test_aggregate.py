from pogoda.aggregate import aggregate_monthly

def test_aggregate_monthly_mean():
    recs = [
        {"T2M":[10]*12, "PRECTOT":[50]*12},
        {"T2M":[12]*12, "PRECTOT":[70]*12},
    ]
    agg = aggregate_monthly(recs)
    assert agg['T2M'][0] == 11
    assert agg['PRECTOT'][0] == 60