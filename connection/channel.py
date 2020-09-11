from abc import ABC, abstractmethod

# Generic Channel object, all the interesting stuff is in DiscordChannel and IrcChannel
class Channel(ABC):
	@abstractmethod
	async def reply(self, message):
		pass

class DiscordChannel(Channel):

	def __init__(self, channel):
		self.channel = channel

	@property
	def rawchannel(self):
		return self.channel

	@property
	def name(self):
		return self.channel.name

	@property
	def users(self):
		return None

	# Some test functions
	@property
	def topic(self):
		return self.channel.topic

	@topic.setter
	def topic(self, topic):
		raise Exception("no topic setting support right now")

	async def reply(self, message):
		await self.channel.send(message)

class IrcChannel(Channel):

	def __init__(self, name, server):
		self._name = name
		self._server = server

	@property
	def name(self):
		return self._name

	@property
	def users(self):
		return None

	async def reply(self, message):
		self._server.raw_send(f"PRIVMSG {self.name} :{message}\n")
