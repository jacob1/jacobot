import string
from abc import abstractmethod

from . import maths
from . import vector

class Tokenizer(object):
    def __init__(self, s):
        """
        :param string: String to tokenize
        """
        # Remove all whitespace:
        self.string = s.translate(str.maketrans("", "", string.whitespace))
        self.tokens = []
        self.itr = 0
        self.buffer = {}

    def tokenize(self):
        TOKENS = [ # Token scan() calls, in order of evaluation
            CommaToken, ParenToken, VectorToken, ConstantOrFunctionToken,
            MinusOrPlusSignToken, BinOpToken, AbstractNumberToken
        ]
        while self.itr < len(self.string):
            found = False
            for token in TOKENS:
                token, i = token.scan(self)
                if token:
                    self.itr = i
                    self.tokens.append(token)
                    found = True
                    break
            if not found:
                raise RuntimeError(f"Unknown input at char {self.itr}: '{self.string[self.itr]}'")
            
        # Magic hack to fix stuff like -3^2 = 9:
        i = 0
        while i < len(self.tokens) - 1:
            token = self.tokens[i]
            if isinstance(token, NumberToken) and token.consumed.startswith("-") and \
                    isinstance(self.tokens[i + 1], BinOpToken) and self.tokens[i + 1].consumed in ["**", "^"]:
                token.consumed = token.consumed[1:] # Remove the - in the number
                self.tokens.insert(i, MinusOrPlusSignToken("-")) # Insert a - operator before
            i += 1

        for matchType in [ParenToken, VectorToken]:
            if self.buffer[f"l{matchType.name}"] > self.buffer[f"r{matchType.name}"]:
                err = f"Mismatched {matchType.name}: Missing closing '{matchType.right_sym}'"
                raise RuntimeError(err)

    def next_char(self, i) -> str:
        """
        Get the char in string at index i + 1
        Returns 1 wide space string if out of bounds
        :return: Next character or 1 wide space string
        """
        if i < 0 or i >= len(self.string) - 1:
            return " "
        return self.string[i + 1]

    def last_non_dummy_token(self):
        """
        :return: Last non-dummy token, or None if none are found
        """
        for token in self.tokens[::-1]:
            if not isinstance(token, AbstractDummyToken):
                return token
        return None
    
    def last_math_token(self):
        """
        :return: Last math token (excludes paren and syntax, includes operators and numbers),
            or None if none are found
        """
        for token in self.tokens[::-1]:
            if not isinstance(token, AbstractDummyToken) and not isinstance(token, MatchableToken):
                return token
        return None



class AbstractToken(object):
    def __init__(self, consumed, argc = 0):
        """
        :param consumed: Token contents, ie a num token might contain "1.5e-5" and a binop token
            might contain "+"
        :param argc: Expected number of args for eval(), or -1 for unlimited
        """
        self.consumed = consumed
        self.argc = argc

    @abstractmethod
    def eval(self, args):
        """
        :param args: Args of function passed as array
        :return: Numeric or other type result
        """
        pass

    @staticmethod
    @abstractmethod
    def scan(tokenizer):
        """
        Scan a string and consume greedily until you reach the next token type
        Return the new token, or None if not applicable, and
        start index of the next token (if new token is not None)
        
        For example, suppose this was a binary operator token, used like this: "A&&B" (Where &&
        is the binary logical AND operator), and string="A&&B" and start_index=1, we would do:

            self.consumed = "&&"
            return 3
        
        Where 3 corresponds to the index of the "B" (start of the next token)

        :param tokenizer: Class to tokenizer. tokenizer.itr will contain start
            index (inclusive) of this token
        :return: AbstractToken | None, next token index
        """

    def __str__(self):
        return f" {self.consumed} "

"""A binary operator, ie '+'"""
class BinOpToken(AbstractToken):
    def __init__(self, consumed):
        super().__init__(consumed, 2)

    def eval(self, args):
        a, b = args
        return maths.BIN_OPS[self.consumed](a, b)

    @staticmethod
    def scan(tokenizer):
        binOpTokens = sorted(maths.BIN_OPS.keys(), key=lambda x: -len(x))

        # A binOp token cannot be the first token and must be in a list of defined operators
        # The previous token must be in this list: ), ], number, constant
        def is_valid(token):
            if token == None:
                return False
            is_constant = isinstance(token, ConstantOrFunctionToken) and not token.is_function
            is_right_paren = isinstance(token, ParenToken) and not token.is_left
            is_right_vector = isinstance(token, VectorToken) and not token.is_left
            return isinstance(token, AbstractNumberToken) or is_right_paren or is_right_vector or is_constant

        if is_valid(tokenizer.last_non_dummy_token()):
            for op in binOpTokens:
                if tokenizer.string[tokenizer.itr:tokenizer.itr + len(op)] == op:
                    return BinOpToken(op), tokenizer.itr + len(op)
        return None, tokenizer.itr

"""A comma"""
class CommaToken(AbstractToken):
    @staticmethod
    def scan(tokenizer):
        if tokenizer.string[tokenizer.itr] == ",":
            return CommaToken(","), tokenizer.itr + 1
        return None, tokenizer.itr

class AbstractDummyToken(AbstractToken):
    pass

"""A dummy start token for function and vector arguments. Added directly by the parser"""
class StartToken(AbstractDummyToken):
    def __init__(self):
        super().__init__("START")

    def eval(self, args):
        return self

class MatchableToken(AbstractToken):
    def __init__(self, consumed, left_sym, right_sym):
        super().__init__(consumed, -1)
        self.is_left = consumed == left_sym
        self.is_right = consumed == right_sym
        assert self.is_left != self.is_right
        self.left_sym = left_sym
        self.right_sym = right_sym

    @staticmethod
    def scan(tokenizer, type):
        """
        A generic scan for paren like symbols
        :param tokenizer: Tokenizer
        :param type: Class to create, assumes constructor (consumed, is_left)
            Must have a static name, left_sym and right_sym property
                name: Unique key for symbol name, ie "paren"
                left_sym: Left symbol, ie '[' (len 1)
                right_sym: Right symbol, ie ']' (len 1)
        :return: constructed token, next itr
        """
        key, left_sym, right_sym = type.name, type.left_sym, type.right_sym
        lkey = f"l{key}"
        rkey = f"r{key}"

        # Ensure buffer keys:
        if not lkey in tokenizer.buffer.keys():
            tokenizer.buffer[lkey] = 0
        if not rkey in tokenizer.buffer.keys():
            tokenizer.buffer[rkey] = 0

        c = tokenizer.string[tokenizer.itr]
        if c in [left_sym, right_sym]:
            if c == left_sym:
                tokenizer.buffer[lkey] += 1
                # Cannot have right before a left, ie )( or )[    
                if len(tokenizer.tokens) and isinstance(tokenizer.tokens[-1], MatchableToken) and \
                        not tokenizer.tokens[-1].is_left:
                    raise RuntimeError(f"Unexpected '{left_sym}' at position {tokenizer.itr}")
            if c == right_sym:
                # Cannot have more right parens than left (running left to right)
                if tokenizer.buffer[lkey] < tokenizer.buffer[rkey] + 1:
                    raise RuntimeError(f"Extraneous '{right_sym}' at position {tokenizer.itr}")
                tokenizer.buffer[rkey] += 1

            return type(c), tokenizer.itr + 1
        return None, tokenizer.itr

"""A paren"""
class ParenToken(MatchableToken):
    left_sym = "("
    right_sym = ")"
    name = "paren"

    def __init__(self, consumed):
        super().__init__(consumed, "(", ")")

    @staticmethod
    def scan(tokenizer):
        return MatchableToken.scan(tokenizer, ParenToken)

"""A vector (square brackets)"""
class VectorToken(MatchableToken):
    left_sym = "["
    right_sym = "]"
    name = "vector"

    def __init__(self, consumed):
        super().__init__(consumed, "[", "]")

    def eval(self, args):
        return vector.Vector(args)

    @staticmethod
    def scan(tokenizer):
        return MatchableToken.scan(tokenizer, VectorToken)

"""A constant or function"""
class ConstantOrFunctionToken(AbstractToken):
    def __init__(self, consumed, is_function):
        argc = 0
        if is_function and consumed not in maths.FUNCTIONS.keys():
            raise RuntimeError(f"Unknown function '{consumed}'")
        if not is_function and consumed not in maths.CONSTANTS.keys():
            raise RuntimeError(f"Unknown constant '{consumed}'")
        
        if is_function:
            argc = maths.FUNCTIONS[consumed].argc

        super().__init__(consumed, argc)
        self.is_function = is_function

    def eval(self, args):
        if not self.is_function:
            return maths.CONSTANTS[self.consumed]
        return maths.FUNCTIONS[self.consumed](args)

    @staticmethod
    def scan(tokenizer):
        c = tokenizer.string[tokenizer.itr]

        # Function names are alphanumeric, starting with alpha
        # Constant names are alphanumeric, starting with alpha, and do not end with a (
        if c.isalpha():
            j = tokenizer.itr
            while tokenizer.next_char(j) in string.ascii_letters + string.digits + "_":
                j += 1
            is_function = tokenizer.next_char(j) == "("
            return ConstantOrFunctionToken(tokenizer.string[tokenizer.itr:j + 1], is_function), j + 1
        return None, tokenizer.itr

"""A +/- but not in front of a number (ie the - in -(1+2))"""
class MinusOrPlusSignToken(AbstractToken):
    def __init__(self, consumed):
        super().__init__(consumed, 1)

    def eval(self, args):
        return (1 if self.consumed == "+" else -1) * args[0]

    @staticmethod
    def scan(tokenizer):
        c = tokenizer.string[tokenizer.itr]

        # Conditions:
        # - previous token (disregarding parens) must be a binop or func op
        # - next token cannot be a digit
        ltoken = tokenizer.last_math_token()
        if c in "+-" and (
                    len(tokenizer.tokens) == 0 or \
                    isinstance(ltoken, BinOpToken) or \
                    (isinstance(ltoken, ConstantOrFunctionToken) and ltoken.is_function)
                ) \
                and not tokenizer.next_char(tokenizer.itr).isdigit():
            return MinusOrPlusSignToken(c), tokenizer.itr + 1
        return None, tokenizer.itr
    
class AbstractNumberToken(AbstractToken):
    @staticmethod
    def scan(tokenizer):
        c = tokenizer.string[tokenizer.itr]
        i = tokenizer.itr
        s = tokenizer.string

        # Cannot have 2 number tokens in a row, ie 0b02 is not 0b0 and 2
        if len(tokenizer.tokens) and isinstance(tokenizer.tokens[-1], AbstractNumberToken):
            return None, tokenizer.itr

        if c in "ij" and tokenizer.next_char(i) not in string.ascii_letters + string.digits:
            return NumberToken("i"), tokenizer.itr + 1

        if c.isdigit() or c in "+-": # Numbers can start with +- or a digit
            if c in "+-":
                i += 1

            # Case: hex number
            if s[i:i + 2] == "0x":
                i += 1
                while tokenizer.next_char(i) in string.hexdigits:
                    i += 1
                if i >= tokenizer.itr + 2:
                    return HexNumberToken(s[tokenizer.itr:i + 1]), i + 1
                return None, tokenizer.itr

            # Case: bin number
            if s[i:i + 2] == "0b":
                i += 1
                while tokenizer.next_char(i) in "01":
                    i += 1
                if i >= tokenizer.itr + 2:
                    return BinNumberToken(s[tokenizer.itr:i + 1]), i + 1
                return None, tokenizer.itr

            # Else: regular number
            counts = {
                "decimal_point" : 0,
                "e_count": 0,
                "+-count": 0
            }
            j = i

            def enforce_valid_number(j, counts):
                c = tokenizer.next_char(j)

                # + or - allowed in exponent, ie 1e+2 or 1e-2
                if c in "+-" and counts["e_count"] > 0 and counts["+-count"] == 0:
                    counts["+-count"] += 1
                    return True

                # Only 1 "e" is allowed
                if c == "e" and counts["e_count"] == 0:
                    counts["e_count"] += 1
                    return True

                # Only 1 decimal point is allowed before the e
                if c == "." and counts["decimal_point"] == 0:
                    counts["decimal_point"] += 1
                    return True
                return False

            while tokenizer.next_char(j).isdigit() or enforce_valid_number(j, counts):
                j += 1
            if tokenizer.next_char(j) in "ij": # Imaginary
                j += 1
            if i != j or s[i].isdigit(): # Single digit or non-zero length
                return NumberToken(s[tokenizer.itr:j + 1]), j + 1
            return None, tokenizer.itr
        return None, tokenizer.itr

"""A number in this format: 0x[A-F0-9]+"""
class HexNumberToken(AbstractNumberToken):
    def eval(self, args):
        return int(self.consumed[2:], 16)

    @staticmethod
    def scan(tokenizer):
        raise NotImplementedError("Call AbstractNumber.scan() instead")

"""A number in this format: 0b[01]+"""
class BinNumberToken(AbstractNumberToken):
    def eval(self, args):
        return int(self.consumed[2:], 2)

    @staticmethod
    def scan(tokenizer):
        raise NotImplementedError("Call AbstractNumber.scan() instead")

"""A number, ie -1.5e-5"""
class NumberToken(AbstractNumberToken):
    def eval(self, args):
        if self.consumed.endswith("i") or self.consumed.endswith("j"):
            return complex(self.consumed.replace("i", "j"))
        if "e" in self.consumed or "." in self.consumed:
            return float(self.consumed)
        return int(self.consumed)

    @staticmethod
    def scan(tokenizer):
        raise NotImplementedError("Call AbstractNumber.scan() instead")
