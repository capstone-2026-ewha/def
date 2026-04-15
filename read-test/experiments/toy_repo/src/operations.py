def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    # BUG: no zero check
    return a / b

def power(a, b):
    # BUG: wrong implementation (should be a ** b)
    return a + b