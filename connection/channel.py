from abc import ABC, abstractmethod

# Generic Channel object, all the interesting stuff is in DiscordChannel and IrcChannel
class Channel(ABC):
	@abstractmethod
	async def reply(self, message):
		pass

	@property
	@abstractmethod
	def name(self) -> str:
		pass

class DiscordChannel(Channel):

	def __init__(self, channel):
		self._channel = channel

	@property
	def rawchannel(self):
		return self._channel

	@property
	def name(self) -> str:
		return self._channel.name

	@property
	def users(self):
		return None

	# Some test functions
	@property
	def topic(self):
		return self._channel.topic

	@topic.setter
	def topic(self, topic):
		raise Exception("no topic setting support right now")

	async def reply(self, message):
		await self._channel.send(message)

class IrcChannel(Channel):

	def __init__(self, name, server):
		self._name = name
		self._server = server

	@property
	def name(self) -> str:
		return self._name

	@property
	def users(self):
		return None

	async def reply(self, message):
		self._server.raw_send(f"PRIVMSG {self.name} :{message}\n")
