import common
from mods.calculator.parse import calc
from mods.calculator.format import format
from mods.calculator.maths import Function, FUNCTIONS, CONSTANTS

from common import *
RegisterMod(__name__)

@command("calc", minArgs=1)
def Calc(message):
	"""(calc <expression>). Does math. Use calchelp to get a list of constants and functions"""
	try:
		expr = message.GetArg(0, endLine=True).strip()
		message.Reply(format(calc(expr)))
	except (ValueError, ArithmeticError, AttributeError, TypeError, RuntimeError) as e:
		message.Reply(str(e))

@command("calchelp")
def Calc(message):
	"""(calchelp [<function>]). Lists functions and constants, or prints information on a function."""
	arg = message.GetArg(0)
	if not arg:
		const_list = ", ".join(CONSTANTS.keys())
		func_list = ", ".join(FUNCTIONS.keys())
		message.Reply(f"Functions: {func_list}")
		message.Reply(f"Constants: {const_list}")
	else:
		func : Function = FUNCTIONS[message.GetArg(0)]
		if not func:
			message.Reply("No such function or constant")
		message.Reply(func.get_help())

@command("calcmc", minArgs=1)
def Calc(message):
	"""(calcmc <expression>). Does math, but also shows counts in stacks."""
	try:
		expr = message.GetArg(0, endLine=True).strip()
		message.Reply(format(calc(expr), True))
	except (ValueError, ArithmeticError, AttributeError, TypeError, RuntimeError) as e:
		message.Reply(str(e))
