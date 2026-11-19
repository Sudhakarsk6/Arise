# name: BMI calculator
# description: Works out your BMI from the height and weight you set, and speaks the result.
# permissions: speak
# category: Health

HEIGHT_CM = 170
WEIGHT_KG = 65


def bmi(height_cm, weight_kg):
    metres = height_cm / 100
    return weight_kg / (metres * metres)


def category(value):
    if value < 18.5:
        return "underweight"
    if value < 25:
        return "in the normal range"
    if value < 30:
        return "overweight"
    return "in the obese range"


def main():
    value = bmi(HEIGHT_CM, WEIGHT_KG)
    text = "Your BMI is %.1f, which is %s. This is a general guide, not medical advice." % (value, category(value))
    arise.speak(text)
    return text


def test_bmi():
    assert round(bmi(170, 65), 1) == 22.5
    assert category(22.5) == "in the normal range" and category(31) == "in the obese range"
