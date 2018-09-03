from common import *
from typing import Optional

import asyncio

@command("ping")
async def PingCmd(message, *, pong : Optional[str]):
	"""PONG"""
	if pong:
		await message.Reply(f"pong {pong}")
	else:
		await message.Reply("pong")

@command("test")
async def TestCmd(message, arg1 : str, arg2 : int):
	await message.Reply("Test: " + arg1 + ", " + str(type(arg2)) + ", " + str(arg2))

@command("test2")
async def Test2Cmd(message, arg1 : str, arg2 : Optional[int], arg3 : str):
	output = [arg1, str(type(arg2)), str(arg2), str(type(arg3)), arg3]
	await message.Reply("Test2: " + ", ".join(output))

@command("test3")
async def Test3Cmd(message, arg1 : RegexArg(r"\#[A-Za-z0-9_-]+")):
	await message.Reply(arg1)

@command("sleep")
async def SleepCmd(message):
	"""sleep test"""
	await asyncio.sleep(5)
	await message.Reply("test")

@command("isadmin")
async def IsAdmin(message):
	"""isadmin"""
	await message.Reply("is admin" if message.sender.IsAdmin() else "is not admin")

@command("whoami")
async def Whoami(message):
	user = message.sender.nick + ", " + message.sender.ident + ", " + message.sender.account + ", " + message.sender.host
	await message.Reply(user)

