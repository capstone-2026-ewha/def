def validate_number(x):
    if not isinstance(x, (int, float)):
        raise TypeError(f"Expected number, got {type(x)}")
    return x

def format_result(result, precision=2):
    if isinstance(result, float):
        return round(result, precision)
    return result