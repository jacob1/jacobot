import numbers
import math
from . import vector

FORMAT_STR = "{:.15g}"
IS_ZERO_PREC = 1e-15

def format_number(result) -> str:
    """
    :param result: A numeric type to be formatted
    :return: string result
    """
    if isinstance(result, complex):
        if abs(result.imag) < IS_ZERO_PREC: # Complex number with very small imaginary part
            real = 0 if abs(result.real) < IS_ZERO_PREC else result.real
            return FORMAT_STR.format(real)
        elif abs(result.real) < IS_ZERO_PREC: # Very small real part:
            imag = 0 if abs(result.imag) < IS_ZERO_PREC else result.imag
            return (FORMAT_STR.format(imag) + "j") \
                .replace("1j", "j") \
                .replace("-1j", "-j")

    if isinstance(result, int): # Ints don't get rounded
        return str(result)

    if abs(result) < IS_ZERO_PREC:
        result = 0
    return FORMAT_STR.format(result)

def format(result, include_mc_calc = False) -> str:
    """
    :param result: Result from calc(), either numeric or a vector
    :param include_mc_calc: Whether to interpret results in stacks of 64 for Minecraft
    :return: Formatted string
    """
    if isinstance(result, vector.Vector):
        contents = ", ".join([format_number(i) for i in result.items])
        return f"[{contents}]"
    elif isinstance(result, numbers.Number):
        mc_str = ""

        # Minecraft required stacks and shulkers
        if not isinstance(result, complex) and include_mc_calc and 0 < result < 1e8:
            r = math.ceil(result)
            stacks = r // 64
            items = r % 64
            shulkers = r // 1728
            stacks_left_over = (r % 1728) // 64

            if stacks > 0 and shulkers == 0:
                mc_str = f" ({stacks}s{items})"
            elif stacks > 0 and shulkers > 0:
                items = "" if items == 0 else items
                stacks_left_over = "" if stacks_left_over == 0 else f"{stacks_left_over}s"
                mc_str = f" ({stacks}s{items} / {shulkers}sh {stacks_left_over}{items})".replace(" )", ")")

        return format_number(result) + mc_str
    return str(result)
