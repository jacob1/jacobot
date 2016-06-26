import string
from common import *

RegisterMod(__name__)

class _calculator(object):
	def __init__(self):
		pass

	def test(self, expression):
		return float(expression)+1

	def _converttonumber(self, expression, isNegative):
		if not "." in expression and not "e" in expression:
			ret = int(expression)
		else:
			ret = float(expression)
		return -ret if isNegative else ret

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

	# Parses a number
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
			elif char == ".":
				if foundE:
					raise ValueError("Found '.' inside e notation at character {0}".format(i+offset))
				if foundDot:
					if not foundInt:
						raise ValueError("Expected number in float at character {0}".format(i+offset))
					return (self._converttonumber(expression[start:i], isNegative), i)
				elif not foundInt:
					start = i
				foundDot = True
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

	def _parse(self, expression, offset):
		i = 0
		parsed = []
		num = True
		while i < len(expression):
			if num:
				(piece, length) = self._getnumber(expression[i:], i+offset)
			else:
				(piece, length) = self._getoperator(expression[i:], i+offset)
			parsed.append(piece)
			i += length
			num = not num
		if num:
			raise ValueError("Expected number to end expression at character {0}".format(i+offset))

		for i in range(len(parsed))[-2::-2]:
			operator = parsed[i]
			if operator == "^":
				(prev, next) = parsed[i-1], parsed[i+1]
				if type(prev) == complex or type(next) == complex:
					raise ValueError("Cannot do exponents on complex numbers")
				parsed = parsed[:i-1] + [float(prev)**float(next)] + parsed[i+2:]
		for i in range(len(parsed))[-2::-2]:
			operator = parsed[i]
			if operator == "*":
				(prev, next) = parsed[i-1], parsed[i+1]
				parsed = parsed[:i-1] + [prev*next] + parsed[i+2:]
			elif operator == "/":
				(prev, next) = parsed[i-1], parsed[i+1]
				parsed = parsed[:i-1] + [prev/next] + parsed[i+2:]
		for i in range(len(parsed))[-2::-2]:
			operator = parsed[i]
			if operator == "+":
				(prev, next) = parsed[i-1], parsed[i+1]
				parsed = parsed[:i-1] + [prev+next] + parsed[i+2:]
			elif operator == "-":
				(prev, next) = parsed[i-1], parsed[i+1]
				parsed = parsed[:i-1] + [prev-next] + parsed[i+2:]
		return parsed[0]

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
			if funcNameStart >= 0 and char not in string.ascii_letters:
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
					(start, funcname) = stack.pop()
					replace = self._calc(expression[start+1:i], start+1)
					if funcname:
						if funcname == "calc" or not hasattr(self, funcname):
							raise ValueError("Not a function: {0}".format(funcname))
						replace = getattr(self, funcname)(replace)
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
def Calc(username, hostmask, channel, text):
	"""(calc <expression>). Does math."""
	try:
		SendMessage(channel, str(calculator.calc(" ".join(text).strip())))
	except (ValueError, ArithmeticError) as e:
		SendMessage(channel, str(e))

