from common import *
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
	from connection.context import Context

@command("test")
async def TestCmd(context : "Context", arg1 : int, arg2 : int):
	"""(test). int, str"""
	await context.reply(", ".join([str(arg1), str(arg2)]))
