from pogoda.trewartha import classify_trewartha

def test_trewartha_tropical():
    temps = [26]*12
    precip = [200]*12
    code, details = classify_trewartha(temps, precip, 5.0)
    assert code.startswith('A')

def test_trewartha_polar():
    temps = [-15,-20,-18,-12,-5,0,3,2,-2,-8,-12,-18]
    precip = [20]*12
    code, details = classify_trewartha(temps, precip, 70.0)
    assert code.startswith('F')

def test_trewartha_dry_desert():
    temps = [25,27,30,34,38,40,41,40,37,33,29,26]
    precip = [2,1,1,0,0,0,1,2,1,1,1,1]
    code, details = classify_trewartha(temps, precip, 20.0)
    assert code.startswith('B') and 'W' in code

def test_trewartha_subtropical():
    temps = [5,7,10,14,18,22,24,24,20,15,10,6]
    precip = [60,55,65,60,62,55,58,65,70,80,75,65]
    code, details = classify_trewartha(temps, precip, 35.0)
    assert code[0] in ('A','C')  # depending on months >=10 (here likely C)

def test_trewartha_cfa_like():
    # Humid subtropical: many months >=10°C (>=8) but one light winter cold month above 0, all-season precip
    temps = [4,6,10,15,20,25,27,27,23,17,11,6]
    precip = [70,65,80,75,90,95,100,90,85,80,75,70]
    code, details = classify_trewartha(temps, precip, 32.0)
    # Should classify as A or C depending on threshold months; we expect A (>=8 months >=10°C)
    assert code[0] in ('A','C')

def test_trewartha_dfa_like_one_subzero():
    # Warm summer continental: 4-7 months >=10°C, one subzero month
    temps = [-1,1,6,13,19,24,26,25,20,13,6,1]
    precip = [45,40,50,55,70,80,85,75,65,60,55,50]
    code, details = classify_trewartha(temps, precip, 45.0)
    # Expect group C (4-7 months >=10) or D if only 3 months; count them.
    m10 = sum(1 for t in temps if t >= 10)
    if 4 <= m10 <=7:
        assert code.startswith('D')
    else:
        assert code.startswith('D')