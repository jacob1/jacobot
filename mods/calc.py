from mods.calculator.parse import calc
from mods.calculator.format import format

from common import *
RegisterMod(__name__)

@command("calc", minArgs=1)
def Calc(message):
	"""(calc <expression>). Does math."""
	try:
		expr = message.GetArg(0, endLine=True).strip()
		message.Reply(format(calc(expr)))
	except (ValueError, ArithmeticError, AttributeError, TypeError, RuntimeError) as e:
		message.Reply(str(e))

@command("calcmc", minArgs=1)
def Calc(message):
	"""(calcmc <expression>). Does math, but also shows counts in stacks."""
	try:
		expr = message.GetArg(0, endLine=True).strip()
		message.Reply(format(calc(expr), True))
	except (ValueError, ArithmeticError, AttributeError, TypeError, RuntimeError) as e:
		message.Reply(str(e))
