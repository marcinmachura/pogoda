from pogoda.year_range import parse_years

def test_single_year():
    assert parse_years("2024") == [2024]

def test_range():
    assert parse_years("2020-2022") == [2020,2021,2022]

def test_mixed():
    assert parse_years("2018,2020-2021,2019") == [2018,2019,2020,2021]

def test_bad_range_order():
    try:
        parse_years("2022-2020")
    except ValueError:
        pass
    else:
        assert False, "Expected ValueError"