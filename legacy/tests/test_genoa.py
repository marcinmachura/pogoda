from pogoda.koppen import classify_koppen
from pogoda.trewartha import classify_trewartha

# Genoa, Italy (approximate monthly means & precip from Wikipedia; means ~ (high+low)/2)
temps = [8.5, 8.9, 10.9, 13.6, 17.7, 21.5, 24.5, 24.7, 21.6, 17.3, 12.5, 9.5]
precip = [142, 117, 119, 103, 81, 64, 32, 73, 135, 163, 158, 154]

def test_genoa_koppen_csa():
    code, details = classify_koppen(temps, precip, 44.4)  # Genoa latitude ~44.4 N
    assert code.startswith('C') and 's' in code and code[2] == 'a'

def test_genoa_trewartha_csa():
    code, details = classify_trewartha(temps, precip, 44.4)
    # Expect subtropical Mediterranean: Csa
    assert code.startswith('C') and code[1] == 's' and code[2] == 'a'