import cmath
import math
from functools import reduce
import operator
import numbers
import random

from . import vector

class Function(object):
    def __init__(self, f, argc):
        """
        :param f: Function to call, (a, b, c...) -> num or other
        :param argc: Number of arguments the function takes
        """
        self.argc = argc
        self.f = f

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


def _angle(args):
    """Angle between two vectors"""
    a, b = args
    return math.acos(a.dot(b) / (abs(a) * abs(b)))

def _angle3(args):
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
    "sin": Function(lambda args: cmath.sin(args[0]), 1),
    "cos": Function(lambda args: cmath.cos(args[0]), 1),
    "tan": Function(lambda args: cmath.tan(args[0]), 1),
    "asin": Function(lambda args: cmath.asin(args[0]), 1),
    "acos": Function(lambda args: cmath.acos(args[0]), 1),
    "atan": Function(lambda args: cmath.atan(args[0]), 1),
    "atan2": Function(lambda args: math.atan2(args[0], args[1]), 2),
    "degrees": Function(lambda args: math.degrees(args[0]), 1),
    "radians": Function(lambda args: math.radians(args[0]), 1),

    "abs": Function(lambda args: cmath.sqrt(sum([abs(x ** 2) for x in args])), -1),
    # Alias
    "norm": Function(lambda args: cmath.sqrt(sum([abs(x ** 2) for x in args])), -1),

    "ceil": Function(lambda args: math.ceil(args[0]), 1),
    "floor": Function(lambda args: math.floor(args[0]), 1),
    "gcd": Function(lambda args: math.gcd(args[0], args[1]), 2),
    "lcm": Function(lambda args: math.lcm(args[0], args[1]), 2),
    "sqrt": Function(lambda args: cmath.sqrt(args[0]), 1),
    "cbrt": Function(lambda args: (args[0]) ** (1/3), 1),

    "exp": Function(lambda args: math.e ** (args[0]), 1),
    "exp2": Function(lambda args: 2 ** (args[0]), 1),
    "log": Function(lambda args: cmath.log(args[0]), 1),
    "ln": Function(lambda args: cmath.log(args[0]), 1),
    "log2": Function(lambda args: math.log2(args[0]), 1),
    "lg": Function(lambda args: math.log2(args[0]), 1),
    "log10": Function(lambda args: math.log10(args[0]), 1),
    "modpow": Function(lambda args: pow(args[0], args[1], args[2]), 3),

    "max": Function(lambda args: max(args), -1),
    "min": Function(lambda args: min(args), -1),
    "sum": Function(lambda args: sum(args), -1),
    "prod": Function(lambda args: reduce(operator.mul, args, 1), -1),

    # Vector functions
    "angle": Function(_angle, 2),
    "angle3": Function(_angle3, 3),
    "sort": Function(lambda args: vector.Vector(sorted(args)), -1),
    "rsort": Function(lambda args: vector.Vector(sorted(args, reverse=True)), -1),
    "len": Function(lambda args: len(args), -1),
    "c2v": Function(_c2v, 1),
    "v2c": Function(_v2c, -1),
    "dot": Function(_dot, 2),
    "cross": Function(_cross, 2),

    # Rand
    "rand": Function(_rand, -1),
    "urand": Function(_urand, -1)
}

CONSTANTS = {
    # Math constants
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "phi": (1 + (5) ** 0.5) / 2,
    "i": (-1) ** 0.5,
    "j": (-1) ** 0.5,
    "sqrt2": 2 ** 0.5,
    
    # Minecraft constants
    "shulker": 1728,
    "stack": 64,
    "dub": 1728 * 2
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
