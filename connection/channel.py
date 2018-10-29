
# Generic Channel object, all the interesting stuff is in DiscordChannel and IrcChannel
class Channel:
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

class IrcChannel(Channel):

	def __init__(self, name):
		self._name = name

	@property
	def name(self):
		return self._name

	@property
	def users(self):
		return None
