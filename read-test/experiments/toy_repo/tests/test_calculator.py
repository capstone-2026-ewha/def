import pytest
from src.calculator import Calculator

def test_add():
    c = Calculator()
    assert c.compute('add', 2, 3) == 5

def test_power():
    c = Calculator()
    assert c.compute('pow', 2, 3) == 8

def test_divide_by_zero():
    c = Calculator()
    with pytest.raises(ZeroDivisionError):
        c.compute('div', 5, 0)