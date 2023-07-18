import cmath
import math
from functools import reduce
import operator
import numbers
import random

from . import vector

class Function(object):
    def __init__(self, f, argc, help=""):
        """
        :param f: Function to call, (a, b, c...) -> num or other
        :param argc: Number of arguments the function takes
        :param help: Informational text which can be displayed
        """
        self.argc = argc
        self.f = f
        self.help = help

    def __call__(self, args):
        if len(args) == 1 and isinstance(args[0], vector.Vector):
            # If there is only 1 vector argument, and the function takes
            # a single argument, the function is applied to every element
            # of the argument, ie sin([0, 1]) -> [sin(0), sin(1)]
            if self.argc == 1:
                return vector.Vector([self.f([x]) for x in args[0]])
            
            # If there is only one vector argument, and the function is vararg, the vector
            # is taken to be the args to the function
            if self.argc == -1:
                return self.f(args[0].items)

        return self.f(args)

    def get_help(self):
        if not self.help:
            return "No information available"

        if self.argc == -1:
            arg_info = " (variable arg count)"
        elif self.argc == 1:
            arg_info = " (1 argument)"
        else:
            arg_info = f" ({self.argc} arguments)"
        return self.help + arg_info


def _log(args):
    """Log of args[1] in base args[0], or natural logarithm of base not provided"""
    if len(args) == 2:
        return cmath.log(args[0], args[1])
    if len(args) == 1:
        return cmath.log(args[0])
    raise RuntimeError("Too many arguments, expected 1 to 2, got " + str(len(args)))

def _angle(args):
    """Angle between two vectors"""
    if not all([isinstance(x, vector.Vector) for x in args]):
        raise RuntimeError("angle() arguments must be Vector")
    a, b = args
    return math.acos(a.dot(b) / (abs(a) * abs(b)))

def _angle3(args):
    if not all([isinstance(x, vector.Vector) for x in args]):
        raise RuntimeError("angle3() arguments must be Vector")
    """Solve for angle between 3 points expressed as vectors"""
    a, center, b = args
    return _angle([a - center, b - center])

def _rand(args):
    if not all([isinstance(x, int) for x in args]):
        raise RuntimeError("Bounds for rand() must be int, use urand() for floats")
    if len(args) == 2:
        return random.randint(args[0], args[1])
    if len(args) == 1:
        return random.randint(0, args[0])
    if len(args) == 0:
        return random.randint(0, 2147483647)
    raise RuntimeError("Too many arguments, expected 0 to 2, got " + str(len(args)))

def _urand(args):
    if not all([isinstance(x, int) or isinstance(x, float) for x in args]):
        raise RuntimeError("Bounds for urand() must be int or float")
    if len(args) == 2:
        return random.uniform(args[0], args[1])
    if len(args) == 1:
        return random.uniform(0, args[0])
    if len(args) == 0:
        return random.uniform(0, 1)
    raise RuntimeError("Too many arguments, expected 0 to 2, got " + str(len(args)))

def _cross(args):
    if not all([isinstance(x, vector.Vector) for x in args]):
        raise RuntimeError("cross() arguments must be Vector")
    return args[0].cross(args[1])

def _dot(args):
    if not all([isinstance(x, vector.Vector) for x in args]):
        raise RuntimeError("dot() arguments must be Vector")
    return args[0].dot(args[1])

def _c2v(args):
    if not isinstance(args[0], numbers.Number):
        raise RuntimeError("c2v() argument must be numeric")
    if isinstance(args[0], complex):
        return vector.Vector([args[0].real, args[0].imag])
    return vector.Vector([args[0], 0])

def _v2c(args):
    v = args[0]
    if not isinstance(v, vector.Vector):
        v = vector.Vector(args)
    if len(v) > 2 or len(v) == 0:
        raise RuntimeError("v2c() vector must have length 1 or 2")
    if len(v) == 1:
        return v[0]
    return complex(v[0], v[1])


FUNCTIONS = {
    "sin": Function(lambda args: cmath.sin(args[0]), 1, "sine of x"),
    "cos": Function(lambda args: cmath.cos(args[0]), 1, "cosine of x"),
    "tan": Function(lambda args: cmath.tan(args[0]), 1, "tangent of x"),
    "asin": Function(lambda args: cmath.asin(args[0]), 1, "arc sine of x"),
    "acos": Function(lambda args: cmath.acos(args[0]), 1, "arc cosine of x"),
    "atan": Function(lambda args: cmath.atan(args[0]), 1, "arc tangent of x"),
    "atan2": Function(lambda args: math.atan2(args[0], args[1]), 2, "arc tangent of y/x"),
    "asinh": Function(lambda args: cmath.asinh(args[0]), 1, "inverse hyperbolic sine of x"),
    "acosh": Function(lambda args: cmath.acosh(args[0]), 1, "inverse hyperbolic cosine of x"),
    "atanh": Function(lambda args: cmath.atanh(args[0]), 1, "inverse hyperbolic tangent of x"),
    "sinh": Function(lambda args: cmath.asinh(args[0]), 1, "hyperbolic sine of x"),
    "cosh": Function(lambda args: cmath.acosh(args[0]), 1, "hyperbolic cosine of x"),
    "tanh": Function(lambda args: cmath.atanh(args[0]), 1, "hyperbolic tangent of x"),
    "degrees": Function(lambda args: math.degrees(args[0]), 1, "convert from radians to degrees"),
    "radians": Function(lambda args: math.radians(args[0]), 1, "convert from degrees to radians"),

    "abs": Function(lambda args: abs(args[0]), 1, "absolute value of x"),
    "ceil": Function(lambda args: math.ceil(args[0]), 1, "rounds up x"),
    "floor": Function(lambda args: math.floor(args[0]), 1, "rounds down x"),
    "gcd": Function(lambda args: math.gcd(args), -1, "greatest common denominator of all arguments"),
    "lcm": Function(lambda args: math.lcm(args), -1, "least common multiple of all arguments"),
    "sqrt": Function(lambda args: cmath.sqrt(args[0]), 1, "square root of x"),
    "cbrt": Function(lambda args: (args[0]) ** (1/3), 1, "cubed root of x"),

    "exp": Function(lambda args: cmath.exp(args[0]), 1, "e^x"),
    "exp2": Function(lambda args: 2 ** (args[0]), 1, "2^x"),
    "pow": Function(lambda args: math.pow(args[0], args[1]), 2, "x^y"),
    "modpow": Function(lambda args: pow(args[0], args[1], args[2]), 3, "(x^y)%z"),
    "log": Function(_log, -1, "1-arg: natural logarithm of x, 2-arg: log x in base y"),
    "ln": Function(lambda args: cmath.log(args[0]), 1, "natural logarithm of x"),
    "log2": Function(lambda args: math.log2(args[0]), 1, "logarithm of x in base 2"),
    "lg": Function(lambda args: math.log2(args[0]), 1, "logarithm of x in base 2"),
    "log10": Function(lambda args: math.log10(args[0]), 1, "logarithm of x in base 10"),

    "norm": Function(lambda args: cmath.sqrt(sum([abs(x ** 2) for x in args])), -1, "Euclidean length of the vector"),

    "max": Function(lambda args: max(args), -1, "maximum of all args"),
    "min": Function(lambda args: min(args), -1, "minimum of all args"),
    "sum": Function(lambda args: sum(args), -1, "sum of all args"),
    "prod": Function(lambda args: reduce(operator.mul, args, 1), -1, "multiply all args"),

    # Vector functions
    "angle": Function(_angle, 2, "angle between two vectors"),
    "angle3": Function(_angle3, 3, "solve for angle between 3 points expressed as vectors"),
    "sort": Function(lambda args: vector.Vector(sorted(args)), -1, "sort all arguments"),
    "rsort": Function(lambda args: vector.Vector(sorted(args, reverse=True)), -1, "reverse sort all arguments"),
    "len": Function(lambda args: len(args), -1, "length of vector"),
    "c2v": Function(_c2v, 1, "converts real and imaginary component of number to vector"),
    "v2c": Function(_v2c, -1, "converts vector to number, first item is the real component and second item is the imaginary component"),
    "dot": Function(_dot, 2, "dot product of vector"),
    "cross": Function(_cross, 2, "cross product of vector"),

    # Rand
    "rand": Function(_rand, -1, "0-arg: random int in range [0, 2^31-1], 1-arg: random int in range [0, x]: 2-arg: random int in range [x, y]"),
    "urand": Function(_urand, -1 , "0-arg: random float in range [0, 1), 1-arg: random float in range [0, x): 2-arg: random float in range [x, y)")
}

CONSTANTS = {
    # Math constants
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "phi": (1 + (5) ** 0.5) / 2,
    "i": (-1) ** 0.5,
    "j": (-1) ** 0.5,
    "sqrt2": 2 ** 0.5
}

BIN_OPS = {
    "**": lambda a, b: a ** b,
    "^": lambda a, b: a ** b,
    "//": lambda a, b: a // b,
    "/": lambda a, b: a / b,
    "*": lambda a, b: a * b,
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "%": lambda a, b: a % b
}
BIN_OPS_PRECEDENCE = { "**": 10, "^": 10, "//": 9, "/": 9, "*": 9, "+": 8, "-": 8, "%": 7 }
