import numbers

from . import maths

class Vector(object):
    def __init__(self, items):
        """
        Construct a vector
        :param items: Array of numeric types contained in this vector
        """

        if not all([isinstance(i, numbers.Number) for i in items]):
            raise RuntimeError("Non-numeric type in vector")
        if len(items) == 0:
            raise RuntimeError("Number of items cannot be empty")
        self.items = items

    @staticmethod
    def _element_wise_op(a, b, op, opname):
        """
        :param a: First parameter, a number or vector
        :param b: 2nd parameter, a number or vector
        :param op: (a, b) -> num where a and b are numbers
        :param opname: Operator name, ie 'addition'
        :return: New vector with result
        """

        if isinstance(a, numbers.Number) and isinstance(b, Vector): # num + vec
            return Vector([op(a, x) for x in b.items])
        if isinstance(b, numbers.Number) and isinstance(a, Vector): # vec + num
            return Vector([op(x, b) for x in a.items])
        if isinstance(a, Vector) and isinstance(b, Vector): # vec + vec
            if len(a) != len(b):
                err = f"Cannot perform {opname}: Vector lengths differ ({len(a)} and {len(b)})"
                raise RuntimeError(err)
            return Vector([op(a[i], b[i]) for i in range(len(a))])

        err = f"Cannot perform {opname} between type '{type(a)}' and '{type(b)}'"
        raise RuntimeError(err)

    def __str__(self):
        items = ", ".join([str(x) for x in self.items])
        return f"[{items}]"
    def __len__(self):
        return len(self.items)
    def __add__(self, other):
        return Vector._element_wise_op(self, other, maths.BIN_OPS['+'], 'addition')
    def __radd__(self, other):
        return self.__add__(other)
    def __sub__(self, other):
        return Vector._element_wise_op(self, other, maths.BIN_OPS['-'], 'subtraction')
    def __rsub__(self, other):
        return Vector._element_wise_op(other, self, maths.BIN_OPS['-'], 'subtraction')
    def __mul__(self, other):
        return Vector._element_wise_op(other, self, maths.BIN_OPS['*'], 'multiplication')
    def __rmul__(self, other):
        return self.__mul__(other)
    def __pow__(self, other):
        return Vector._element_wise_op(self, other, maths.BIN_OPS['^'], 'exponentiation')
    def __rpow__(self, other):
        return Vector._element_wise_op(other, self, maths.BIN_OPS['^'], 'exponentiation')
    def __truediv__(self, other):
        return Vector._element_wise_op(self, other, maths.BIN_OPS['/'], 'division')
    def __rtruediv__(self, other):
        return Vector._element_wise_op(other, self, maths.BIN_OPS['/'], 'division')
    def __floordiv__(self, other):
        return Vector._element_wise_op(self, other, maths.BIN_OPS['//'], 'integer division')
    def __rfloordiv__(self, other):
        return Vector._element_wise_op(other, self, maths.BIN_OPS['//'], 'integer division')
    def __mod__(self, other):
        return Vector._element_wise_op(self, other, maths.BIN_OPS['%'], 'modular division')
    def __rmod__(self, other):
        return Vector._element_wise_op(other, self, maths.BIN_OPS['%'], 'modular division')
    def __getitem__(self, key):
        return self.items[key]
    def __abs__(self):
        return sum([abs(x ** 2) for x in self.items]) ** 0.5

    def dot(self, other):
        if len(other) != len(self):
            err = f"Cannot dot() with vectors of different lengths ({len(self)} and {len(other)})"
            raise RuntimeError(err)
        s = 0
        for i, item in enumerate(other.items):
            s += item * self.items[i]
        return s
    
    def cross(self, other):
        if len(other) != len(self):
            err = f"Cannot dot() with vectors of different lengths ({len(self)} and {len(other)})"
            raise RuntimeError(err)
        if len(self) != 3:
            raise RuntimeError("Cross product is only implemented for vectors of length 3")
        a, b = self, other
        return Vector([
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]
        ])
