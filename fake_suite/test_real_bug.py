def calculate_total(price, quantity):
    return price * quantity + 1  # bug: adds an extra dollar

def test_cart_total():
    assert calculate_total(10, 2) == 20