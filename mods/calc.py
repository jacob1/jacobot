import string
import math

from common import *
RegisterMod(__name__)

class _calculator(object):
	def __init__(self):
		pass

	# Functions go here, any function in this class not starting in _ can be called by the calculator
	"""def pow(self, expression, offset):
		pieces = expression.split(",")
		num = self._parse(pieces[0], offset)
		root = self._parse(pieces[1], offset+len(pieces[0])+1)
		return math.pow(num, root)

	def sqrt(self, expression, offset):
		pieces = expression.split(",")
		num = self._parse(pieces[0], offset)
		return math.sqrt(num)"""

	# Convert a string to a number (string is assumed to actually be a number)
	def _converttonumber(self, expression, isNegative):
		if not "." in expression and not "e" in expression:
			ret = int(expression)
		else:
			ret = float(expression)
		return -ret if isNegative else ret

	# Convert a string to a complex number (python built-in)
	def _getcomplex(self, expression, offset):
		if expression[0] != "(":
			raise ValueError("Expected complex number at character {0}".format(offset))
		(real, length) = self._getnumber(expression[1:], offset+1)
		(compl, length2) = self._getnumber(expression[1+length:], offset+1+length)
		if expression[1+length+length2] != "j":
			raise ValueError("Expected complex number 'j' at character {0}".format(offset+1+length+length2))
		if expression[2+length+length2] != ")":
			raise ValueError("Expected complex number closing ')' at character {0}".format(offset+2+length+length2))
		return (complex(expression[:3+length+length2]), 3+length+length2)

	# Parses something that is assumed to be a number, stops parsing when the next character would be an operator / invalid in a number
	def _getnumber(self, expression, offset):
		if expression[0] == "(":
			return self._getcomplex(expression, offset)

		start = 0
		foundInt = False
		foundDot = False
		foundE = False
		foundEExponent = False
		isNegative = False
		for i in range(len(expression)):
			char = expression[i]
			# Allows unlimited -s and +s before the number starts. Once it starts, anything after is assumed to be an operator and number parsing stops
			if char == "-" or char == "+":
				if foundInt and (not foundE or foundEExponent):
					return (self._converttonumber(expression[start:i], isNegative), i)
				if char == "-":
					isNegative = not isNegative
				elif char == "+":
					isNegative = False
			elif char in string.digits:
				if not foundInt:
					foundInt = True
					if not foundDot:
						start = i
				if foundE:
					foundEExponent = True
			# Only one dot is allowed. Any subsequent dots are assumed to be an operator and number parsing stops
			elif char == ".":
				if foundDot:
					if not foundInt and not foundE:
						raise ValueError("Expected number in float at character {0}".format(i+offset))
					return (self._converttonumber(expression[start:i], isNegative), i)
				elif not foundInt:
					start = i
				foundDot = True
			# Ignore whitespace (maybe it shouldn't always ignore whitespace though)
			elif char in string.whitespace:
				continue
			elif char == "e":
				if foundE:
					raise ValueError("Found extra 'e' at character {0}".format(i+offset))
				if foundInt:
					foundE = True
			else:
				if not foundInt:
					raise ValueError("Expected number at character {0}".format(i+offset))
				return (self._converttonumber(expression[start:i], isNegative), i)
		if not foundInt:
			raise ValueError("Expected bagels at character {0}".format(i+offset))
		return (self._converttonumber(expression[start:], isNegative), len(expression))

	# Parses looking for an operator
	def _getoperator(self, expression, offset):
		for i in range(len(expression)):
			char = expression[i]
			if char in string.whitespace:
				continue
			elif char in "^*/+-":
				return (expression[:i+1], i+1)
			else:
				break
		raise ValueError("Expected operator at character {0}".format(i+offset))

	# Parses an arbitrary expression without any function calls or parenthesis
	def _parse(self, expression, offset):
		i = 0
		parsed = []
		num = True
		# Alternate looking for numbers and operators, and put the results into parsed[]
		while i < len(expression):
			if num:
				(piece, length) = self._getnumber(expression[i:], i+offset)
			else:
				(piece, length) = self._getoperator(expression[i:], i+offset)
			parsed.append(piece)
			i += length
			num = not num
		# Can't end in an operator
		if not parsed:
			raise ValueError("Empty expression at character {0}".format(i+offset))
		if num:
			raise ValueError("Expected number to end expression at character {0}".format(i+offset))

		# Continuously loop through parsed, doing operations in the order of operations
		i = 1
		while i < len(parsed):
			operator = parsed[i]
			if operator == "^":
				(prev, next) = parsed[i-1], parsed[i+1]
				if type(prev) == complex or type(next) == complex:
					raise ValueError("Cannot do exponents on complex numbers")
				# Convert to float to prevent DOS
				parsed = parsed[:i-1] + [float(prev)**float(next)] + parsed[i+2:]
			else:
				i += 2
		i = 1
		while i < len(parsed):
			operator = parsed[i]
			if operator == "*":
				(prev, next) = parsed[i-1], parsed[i+1]
				parsed = parsed[:i-1] + [prev*next] + parsed[i+2:]
			elif operator == "/":
				(prev, next) = parsed[i-1], parsed[i+1]
				parsed = parsed[:i-1] + [prev/next] + parsed[i+2:]
			else:
				i += 2
		i = 1
		while i < len(parsed):
			operator = parsed[i]
			if operator == "+":
				(prev, next) = parsed[i-1], parsed[i+1]
				parsed = parsed[:i-1] + [prev+next] + parsed[i+2:]
			elif operator == "-":
				(prev, next) = parsed[i-1], parsed[i+1]
				parsed = parsed[:i-1] + [prev-next] + parsed[i+2:]
			else:
				i += 2
		return parsed[0]

	# Parses an expression, looking for any function calls and parenthesis and replacing those with a _parse result
	# functions don't function at the moment
	def _calc(self, expression, offset=0):
		if not "(" in expression and not ")" in expression:
			return self._parse(expression, offset)

		stack = []
		funcNameStart = -1
		i = 0
		while True:
			if i >= len(expression):
				break
			char = expression[i]
			if funcNameStart >= 0 and char not in string.ascii_letters and not (char == ")" and i > 0 and expression[i-1] == "j"):
				if char == "(":
					stack.append((i, expression[funcNameStart:i]))
					funcNameStart = -2
				else:
					raise ValueError("Expected '(' at character {0}".format(i+offset))
			elif char == "(":
				stack.append((i,None))
			elif char in string.ascii_letters:
				if funcNameStart == -1:
					funcNameStart = i
			elif char == ")":
				if stack:
					funcNameStart = -1
					(start, funcname) = stack.pop()
					if not funcname and i > 0 and expression[i-1] == "j":
						self._getcomplex(expression[start:], offset)
						i = i + 1
						continue
					replace = self._calc(expression[start+1:i], start+1)
					if funcname:
						if funcname == "calc" or not hasattr(self, funcname):
							raise ValueError("Not a function: {0}".format(funcname))
						replace = getattr(self, funcname)(replace, i+offset)
						start = start - len(funcname)
					replace = str(replace)
					expression = expression[:start] + replace + expression[i+1:]
					i = start + len(replace)
					continue
				else:
					raise ValueError("Extra ')' at character {0} test: {1}".format(i+offset, expression))
			i = i + 1
		if stack:
			raise ValueError("Missing {0} closing ')'{1}".format(len(stack), "" if len(stack) == 1 else "s"))
		return self._parse(expression, offset)

	def calc(self, expression):
		return self._calc(expression)
calculator = _calculator()

@command("calc", minArgs=1)
def Calc(message):
	"""(calc <expression>). Does math."""
	try:
		message.Reply(str(calculator.calc(message.GetArg(0, endLine=True).strip())))
	except (ValueError, ArithmeticError) as e:
		message.Reply(str(e))

