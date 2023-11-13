from common import *
from typing import Optional, TYPE_CHECKING

import asyncio

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
	await context.reply("Test: " + arg1 + ", " + str(type(arg2)) + ", " + str(arg2))

@command("test2")
async def Test2Cmd(context : "Context", arg1 : str, arg2 : Optional[int], arg3 : str):
	output = [arg1, str(type(arg2)), str(arg2), str(type(arg3)), arg3]
	await context.reply("Test2: " + ", ".join(output))

@command("test3")
async def Test3Cmd(context : "Context", arg1 : RegexArg(r"\#[A-Za-z0-9_-]+")):
	await context.reply(arg1)

@command("sleep")
async def SleepCmd(context : "Context"):
	"""sleep test"""
	await asyncio.sleep(5)
	await context.reply("test")

@command("isadmin")
async def IsAdmin(context: "Context"):
	"""isadmin"""
	await context.reply("is admin" if context.sender.is_owner() else "is not admin")

@command("whoami")
async def Whoami(context : "Context"):
	#user = message.sender.nick + ", " + message.sender.ident + ", " + message.sender.account + ", " + message.sender.host
	user = context.sender.nick + ", " + str(context.sender.account_name)
	await context.reply(user)

