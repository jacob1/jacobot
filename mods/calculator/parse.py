from . import lexer
from . import maths

def _token_is_left_paren(t):
    return isinstance(t, lexer.ParenToken) and t.is_left
def _token_is_function(t):
    return isinstance(t, lexer.ConstantOrFunctionToken) and t.is_function
def _token_is_constant(t):
    return isinstance(t, lexer.ConstantOrFunctionToken) and not t.is_function
def _token_is_left_vector(t):
    return isinstance(t, lexer.VectorToken) and t.is_left
def _is_left_matchable(t):
    return isinstance(t, lexer.MatchableToken) and t.is_left

def shunting_yard(tokenizer):
    """
    :param tokens: Tokenizer with tokenized expression
    :return: Out stack
    """
    # These should be caught in lexer so these error messages
    # shouldn't display
    def mismatch_error(type):
        return f"Error: mismatched {type.name} {type.left_sym}{type.right_sym}"

    # Plan: first parse func nodes, then paren nodes, then vector nodes
    # then bin expr
    out_stack = []
    op_stack = []

    def _match_right_close(left_token_check_func, mismatch_error_msg):
        """
        Match a closing paren-like pair (ie (a, b, c) or [1, 2, 3])
        Called when the right token is reached, the left_token_check_func accepts
        a token and returns if it is the left token

        :param left_token_check_func: token -> bool (is left token)
        :param mismatch_error_msg: Error message to throw on mismatch
        :return: The left token
        """
        if not len(op_stack):
            raise RuntimeError(mismatch_error_msg)

        # While top is not left token (ie ( or [)
        while not left_token_check_func(op_stack[-1]):
            if not len(op_stack):
                raise RuntimeError(mismatch_error_msg)
            out_stack.append(op_stack.pop())

        if not (len(op_stack) and left_token_check_func(op_stack[-1])):
            raise RuntimeError(mismatch_error_msg)
        return op_stack.pop()
    
    def _precedence(token):
        """
        Return precedence of token, higher = first
        :param token:
        :return: Precedence
        """
        if isinstance(token, lexer.BinOpToken):
            return maths.BIN_OPS_PRECEDENCE[token.consumed]
        if isinstance(token, lexer.MinusOrPlusSignToken):
            return maths.BIN_OPS_PRECEDENCE["^"] - 0.01 # +/- above multiplication, but less than power
        return 999999

    # Shunting yard algorithm
    for token in tokenizer.tokens:
        if isinstance(token, lexer.AbstractNumberToken) or _token_is_constant(token):
            out_stack.append(token)

        elif _token_is_function(token) or isinstance(token, lexer.MinusOrPlusSignToken):
            while len(op_stack) and _precedence(token) <= _precedence(op_stack[-1]) \
                    and not _is_left_matchable(op_stack[-1]):
                out_stack.append(op_stack.pop())
            op_stack.append(token)
    
        elif isinstance(token, lexer.BinOpToken):
            # Note: assumes all math operators are left-associative
            while \
                    len(op_stack) and not _is_left_matchable(op_stack[-1]) and \
                    _precedence(token) <= _precedence(op_stack[-1]):
                out_stack.append(op_stack.pop())
            op_stack.append(token)

        elif isinstance(token, lexer.CommaToken):
            # While top is not left ( or [
            while not _is_left_matchable(op_stack[-1]):
                out_stack.append(op_stack.pop())

        elif _is_left_matchable(token): # Left paren or vector
            out_stack.append(lexer.StartToken())
            op_stack.append(token)

        elif isinstance(token, lexer.ParenToken) and not token.is_left: # Right paren
            _match_right_close(_token_is_left_paren, mismatch_error(type(token)))
            if len(op_stack) and _token_is_function(op_stack[-1]): # Account for func() usage
                out_stack.append(op_stack.pop())
            else:
                # Remove last START token, since not needed (not a function)
                for i in range(len(out_stack) - 1, -1, -1):
                    if isinstance(out_stack[i], lexer.ConstantOrFunctionToken) and out_stack[i].is_function:
                        break
                    if isinstance(out_stack[i], lexer.StartToken):
                        out_stack.pop(i)
                        break

        elif isinstance(token, lexer.VectorToken) and not token.is_left: # Right vector
            left = _match_right_close(_token_is_left_vector, mismatch_error(type(token)))
            out_stack.append(left) # Add [ to out stack as vector operator

        else:
            err = f"Unimplemented token: {token}"
            raise RuntimeError(err)

    while len(op_stack):
        if isinstance(token, lexer.MatchableToken) and token.is_left:
            raise RuntimeError(mismatch_error(type(token)))
        out_stack.append(op_stack.pop())

    return out_stack

def parse(expr):
    """
    :param expr: Expression to parse
    :return: Result of the expression
    """
    out_stack = shunting_yard(expr)
    stack = []

    def get_n_tokens(n):
        """
        Attempt tp consume n tokens from the stack. If n == -1 then will
        consume until a start token is hit. If the number of arguments detected
        does not match n and n >= 0 this will throw an error

        :param n: Number of tokens to consume, or -1 for vararg functions
        :return: Array of args in forward order
        """
        args = []
        while ((n >= 0 and len(args) < n) or n == -1) and len(stack) and not isinstance(stack[-1], lexer.StartToken):
            t = stack.pop()
            if not isinstance(t, lexer.StartToken):
                args.append(t)

        if len(args) != n and n >= 0:
            err = f"Invalid number of arguments (expected {n}, got {len(args)})"
            raise RuntimeError(err)
        if n != 0 and len(stack) and isinstance(stack[-1], lexer.StartToken):
            stack.pop() # Remove the START token if scanning a function or vector

        return args[::-1]

    for token in out_stack:
        val = token.eval(get_n_tokens(token.argc))
        if val != None:
            stack.append(val)

    if not len(stack):
        raise RuntimeError("Failed to evaluate result (missing parentheses?)")

    return stack[-1]

def calc(expr):
    """
    Calculate an expression
    :param expr: Expression to calc, ie "1 + 1"
    :return: Numeric answer
    """
    t = lexer.Tokenizer(expr)
    t.tokenize()
    return parse(t)
