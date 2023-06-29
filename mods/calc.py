import string
import math

from common import *
RegisterMod(__name__)

class _calculator(object):
	def __init__(self):
		pass

	def _expectargs(self, args, num, offset):
		if len(args) < num:
			raise ValueError("Expected at least {0} arguments, got {1} in function at character {2}".format(num, len(args), offset))

	# Functions go here, any function in this class not starting in _ can be called by the calculator
	"""def pow(self, expression, offset):
		pieces = expression.split(",")
		num = self._parse(pieces[0], offset)
		root = self._parse(pieces[1], offset+len(pieces[0])+1)
		return math.pow(num, root)"""

	"""def sqrt(self, expression, offset):
		return 1.41421356237
		#pieces = expression.split(",")
		#num = self._parse(pieces[0], offset)
		#return math.sqrt(num)"""

	def pow(self, args, offset):
		self._expectargs(args, 2, offset)
		return math.pow(args[0], args[1])

	def sqrt(self, args, offset):
		self._expectargs(args, 1, offset)
		return args[0]**0.5

	def log(self, args, offset):
		self._expectargs(args, 1, offset)
		if len(args) > 1:
			return math.log(args[0], args[1])
		return math.log(args[0])

	def log2(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.log2(args[0])

	def log10(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.log10(args[0])

	def exp(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.exp(args[0])

	def cos(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.cos(args[0])

	def sin(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.sin(args[0])

	def tan(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.tan(args[0])

	def acos(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.acos(args[0])

	def asin(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.asin(args[0])

	def atan(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.atan(args[0])

	def atan2(self, args, offset):
		self._expectargs(args, 2, offset)
		return math.atan2(args[0], args[1])

	def acosh(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.acosh(args[0])

	def asinh(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.asinh(args[0])

	def atanh(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.atanh(args[0])

	def cosh(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.cosh(args[0])

	def sinh(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.sinh(args[0])

	def tanh(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.tanh(args[0])

	def abs(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.fabs(args[0])

	def ceil(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.ceil(args[0])

	def floor(self, args, offset):
		self._expectargs(args, 1, offset)
		return math.floor(args[0])


	# Convert a string to a number (string is assumed to actually be a number)
	def _converttonumber(self, expression, isNegative):
		if not "." in expression and not "e" in expression:
			ret = int(expression)
		else:
			ret = float(expression)
		return -ret if isNegative else ret

	# Convert a string to a complex number (python built-in)
	def _getcomplex(self, expression, offset):
		offset2 = 0
		while expression[offset2] in string.whitespace:
			offset2 = offset2 + 1
		if expression[offset2] != "(":
			raise ValueError("Expected complex number at character {0}".format(offset))
		(real, length) = self._getnumber(expression[offset2+1:], offset+offset2+1)
		(compl, length2) = self._getnumber(expression[offset2+1+length:], offset+offset2+1+length)
		real = round(real, 10)
		if expression[offset2+1+length+length2] != "j":
			raise ValueError("Expected complex number 'j' at character {0}".format(offset+offset2+1+length+length2))
		if expression[offset2+2+length+length2] != ")":
			raise ValueError("Expected complex number closing ')' at character {0}".format(offset+offset2+2+length+length2))
		return (complex(real, compl), 3+length+length2+offset2)
		#return (complex(expression[offset2:offset2+3+length+length2]), 3+length+length2+offset2)

	# Parses something that is assumed to be a number, stops parsing when the next character would be an operator / invalid in a number
	def _getnumber(self, expression, offset):
		start = 0
		foundInt = False
		foundDot = False
		foundE = False
		foundEExponent = False
		checkedComplex = False
		isNegative = False
		for i in range(len(expression)):
			char = expression[i]
			if not checkedComplex and char not in string.whitespace:
				if char == "(":
					return self._getcomplex(expression, offset)
				checkedComplex = True
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
			raise ValueError("Expected bagels at character {0}".format(offset))
		return (self._converttonumber(expression[start:], isNegative), len(expression))

	# Parses looking for an operator
	def _getoperator(self, expression, offset):
		for i in range(len(expression)):
			char = expression[i]
			if char in string.whitespace:
				continue
			elif char in "^*/+-%":
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
				exp = float(prev)**float(next)
				if type(exp) == complex:
					exp = complex(round(exp.real, 10), exp.imag)
				parsed = parsed[:i-1] + [exp] + parsed[i+2:]
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
			elif operator == "%":
				(prev, next) = parsed[i-1], parsed[i+1]
				parsed = parsed[:i-1] + [prev%next] + parsed[i+2:]
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
			if funcNameStart >= 0 and char not in string.ascii_letters and char not in string.digits and not (char == ")" and i > 0 and expression[i-1] == "j"):
				if char == "(":
					stack.append((i, expression[funcNameStart:i]))
					funcNameStart = -2
				else:
					funcNameStart = -1
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

					funcret = ""
					if funcname:
						# Split function arguments on commas
						pieces = expression[start+1:i].split(",")
						args = []
						argpos = start+1
						for piece in pieces:
							args.append(self._parse(piece, argpos))
							argpos += len(piece)+1

						if funcname == "calc" or not hasattr(self, funcname):
							raise ValueError("Not a function: {0}".format(funcname))
						funcret = str(getattr(self, funcname)(args, start+1+offset))
						start = start - len(funcname)
					else:
						funcret = str(self._calc(expression[start+1:i]))

					expression = expression[:start] + funcret + expression[i+1:]
					i = start + len(funcret)
					continue
				else:
					raise ValueError("Extra ')' at character {0}".format(i+offset))
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

