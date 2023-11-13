from connection.context import Context


class MockContext(Context):
	def __init__(self, connection_type: str, server_name: str, server, sender, receiver):
		super().__init__(connection_type, server_name, server, sender, receiver)
		self.last_reply_type = None
		self.last_reply = None

	async def reply(self, message):
		self.last_reply_type = "reply"
		self.last_reply = message
		await self.receiver.reply(message)

	async def reply_in_private(self, message):
		self.last_reply_type = "reply_in_private"
		self.last_reply = message
		await self.sender.reply(message)

	async def reply_in_notice(self, message):
		self.last_reply_type = "reply_in_notice"
		self.last_reply = message
		await self.sender.reply_in_notice(message)
