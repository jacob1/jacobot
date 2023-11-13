from common import *
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
	from connection.context import Context

@command("ping")
async def PingCmd(context : "Context", *, pong : str|None):
	"""PONG"""
	if pong:
		await context.reply(f"pong {pong}")
	else:
		await context.reply("pong")

@command("test")
async def TestCmd(context : "Context", arg1 : str, arg2 : int):
	"""(test). str, int"""
	await context.reply(", ".join([str(arg1), str(arg2)]))

@command("fake_test_plugin")
async def TestCmd(context : "Context"):
	"""(fake_test_plugin)"""
	await context.reply("Plugin 1")

@command("fake_test_plugin_2")
async def TestCmd(context : "Context"):
	"""(fake_test_plugin_2)"""
	await context.reply("Plugin 1 reply")

@command("optionals")
async def OptionalsCmd(context : "Context", arg1 : str, arg2 : Optional[int], arg3 : Optional[str], arg4 : Optional[int]):
	await context.reply(", ".join([arg1, str(arg2), str(arg3), str(arg4)]))

@command("optionals2")
async def Optionals2Cmd(context : "Context", arg1 : int, arg2 : Optional[int], arg3 : Optional[str], arg4 : Optional[int]):
	await context.reply(", ".join([str(arg1), str(arg2), str(arg3), str(arg4)]))

@command("optionals3")
async def Optionals3Cmd(context : "Context", arg1 : Optional[int], arg2 : Optional[str], arg3 : int):
	await context.reply(", ".join([str(arg1), str(arg2), str(arg3)]))

@command("optionals4")
async def Optionals4Cmd(context : "Context", arg1 : Optional[ExactMatchArg("--arg1")], arg2 : Optional[ExactMatchArg("--arg2")],
						arg3 : Optional[RegexArg(".*arg.*")], arg4: str):
	await context.reply(", ".join([str(arg1), str(arg2), str(arg3), str(arg4)]))

@command("optionals5")
async def Optionals5Cmd(context : "Context", arg1 : int, arg2 : int, arg3 : Optional[str], arg4 : Optional[int]):
	await context.reply(", ".join([str(arg1), str(arg2), str(arg3), str(arg4)]))

@command("isadmin")
async def IsAdmin(context: "Context"):
	"""isadmin"""
	await context.reply("is admin" if context.sender.is_owner() else "is not admin")

@command("whoami")
async def Whoami(context : "Context"):
	#user = message.sender.nick + ", " + message.sender.ident + ", " + message.sender.account + ", " + message.sender.host
	user = context.sender.nick + ", " + str(context.sender.account_name)
	await context.reply(user)

