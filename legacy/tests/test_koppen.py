from pogoda.koppen import classify_koppen

# Synthetic simple tests for a few classes

def test_cfb_like():
    # Oceanic: mild summers, no dry season
    temps = [2,3,6,9,13,16,18,18,15,11,7,4]
    precip = [60,55,65,60,62,55,58,65,70,80,75,65]
    code, details = classify_koppen(temps, precip, latitude=50.0)
    assert code.startswith('C')


def test_bw_hot():
    temps = [18,20,24,28,32,35,37,36,33,28,23,19]
    precip = [1,2,0,1,0,0,1,2,1,1,1,1]
    code, details = classify_koppen(temps, precip, latitude=25.0)
    assert code.startswith('B') and 'W' in code


def test_et():
    temps = [-20,-18,-15,-10,-5,0,4,3,0,-5,-12,-18]
    precip = [10]*12
    code, details = classify_koppen(temps, precip, latitude=70.0)
    assert code == 'ET'


def test_trewartha_dfa_like_one_subzero():
    # Warm summer continental: 4-7 months >=10°C, one subzero month
    temps = [-4,1,6,13,19,24,26,25,20,13,6,1]
    precip = [45,40,50,55,70,80,85,75,65,60,55,50]
    code, details = classify_koppen(temps, precip, 45.0)
    # Expect group C (4-7 months >=10) or D if only 3 months; count them.
    assert code.startswith('D')
