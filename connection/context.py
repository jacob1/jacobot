from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from connection.channel import *
	from connection.server import *
	from connection.user import *


# Context class, stores information on the location an event took place and who triggered it
# This is a component in most events like MessageEvent
class Context:

	def __init__(self, server: "Server", sender : "User", receiver):
		self.server = server
		self.sender = sender
		self.receiver = receiver

	async def reply(self, message):
		await self.receiver.reply(message)

	async def reply_in_private(self, message):
		await self.sender.reply(message)

	async def reply_in_notice(self, message):
		await self.sender.reply_in_notice(message)

	def is_private(self):
		return isinstance(self.receiver, User)
