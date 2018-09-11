
# Generic Channel object, all the interesting stuff is in DiscordChannel and IrcChannel
class Channel:
	pass

class DiscordChannel(Channel):

	def __init__(self, channel):
		self.channel = channel

	@property
	def rawchannel(self):
		return self.channel

	# Some test functions
	@property
	def topic(self):
		return self.channel.topic

	@topic.setter
	def topic(self, topic):
		raise Exception("no topic setting support right now")
