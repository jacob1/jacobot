from connection.user import *

# Context class, stores information on the location an event took place and who triggered it
# This is a component in most events like MessageEvent
class Context:

	def __init__(self, server, sender, receiver):
		self.server = server
		self.sender = sender
		self.receiver = receiver

	async def reply(self, message):
		if isinstance(self.receiver, User):
			await self.reply_in_private(message)
		else:
			await self.server.reply(self.receiver, message)

	async def reply_in_private(self, message):
		await self.server.reply_in_private(self.sender, message)

	async def reply_in_notice(self, message):
		await self.server.reply_in_notice(self.sender, message)

	def is_private(self):
		return isinstance(self.receiver, User)

