from src.operations import add, subtract, multiply, divide, power
from src.utils import validate_number, format_result

class Calculator:
    def __init__(self):
        self.history = []

    def compute(self, op, a, b):
        a = validate_number(a)
        b = validate_number(b)

        ops = {
            'add': add,
            'sub': subtract,
            'mul': multiply,
            'div': divide,
            'pow': power,
        }
        if op not in ops:
            raise ValueError(f"Unknown op: {op}")

        result = ops[op](a, b)
        result = format_result(result)
        self.history.append((op, a, b, result))
        return result