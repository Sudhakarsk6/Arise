# name: EMI calculator
# description: Monthly loan EMI and total interest, spoken aloud.
# permissions: speak
# category: Finance

PRINCIPAL = 500000      # loan amount
ANNUAL_RATE = 9.5       # percent per year
MONTHS = 60


def emi(principal, annual_rate, months):
    r = annual_rate / 12 / 100
    if r == 0:
        return principal / months
    growth = (1 + r) ** months
    return principal * r * growth / (growth - 1)


def main():
    monthly = emi(PRINCIPAL, ANNUAL_RATE, MONTHS)
    interest = monthly * MONTHS - PRINCIPAL
    text = "Your monthly EMI is %d rupees. Total interest over %d months is %d rupees." % (round(monthly), MONTHS, round(interest))
    arise.speak(text)
    return text


def test_emi():
    assert round(emi(100000, 12, 12), 2) == 8884.88
    assert emi(1200, 0, 12) == 100
