from __future__ import annotations
from connection.user import User

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from connection.channel import Channel
	from connection.server import Server

class ConnectionDescriptor:
	def __init__(self, connection_type : str, server_name : str):
		self.connection_type = connection_type
		self.server_name = server_name

	def __str__(self):
		return f"{self.connection_type}-{self.server_name}"

	def __hash__(self):
		return str(self).__hash__()

	def __eq__(self, other):
		return str(self).__eq__(str(other))

# Context class, stores information on the location an event took place and who triggered it
# This is a component in most events like MessageEvent
class Context:

	def __init__(self, connection_type : str, server_name : str, server: Server, sender : User, receiver : User|Channel):
		self.connection_type = connection_type
		self.server_name = server_name
		self.server = server
		self.sender = sender
		self.receiver = receiver

	async def reply(self, message):
		if self.is_private():
			await self.sender.reply(message)
		else:
			await self.receiver.reply(message)

	async def reply_in_private(self, message):
		await self.sender.reply(message)

	async def reply_in_notice(self, message):
		await self.sender.reply_in_notice(message)

	def is_private(self):
		return isinstance(self.receiver, User)

	def get_connection_descriptor(self):
		"""Get a descriptor for this context, can be converted to string as an identifier for this context's server"""
		return ConnectionDescriptor(self.connection_type, self.server_name)
