import discord

from event import *
from connection.channel import *
from connection.context import *
from connection.user import *

# Generic Server class, subclasses (DiscordServer and IrcServer) will implement connection and send out events
class Server:
	pass

class DiscordServer(Server):

	def __init__(self, token, event_handler):
		global server_instance

		self.client = discord.Client()
		self.token = token
		self.event_handler = event_handler

	@property
	def client(self):
		return self._client

	@client.setter
	def client(self, client):
		self._client = client
		client.event(self.on_message)

	async def on_message(self, message):
		if message.author == self.client.user:
			return

		sender = DiscordUser(message.author)

		if message.channel.is_private:
			# TODO: consider supporting this. Not very important and not compatible with IRC though
			if len(message.channel.recipients) != 1:
				return
			# message.channel is a PrivateChannel instance here
			receiver = DiscordUser(message.channel)
		else:
			receiver = DiscordChannel(message.channel)

		context = Context(self, sender, receiver)
		await self.event_handler(MessageEvent(context, message.content))

	# TODO: client.run is wrong and blocks forever
	def connect(self):
		self._client.run(self.token)
		self.token = None # Clear for security reasons

	async def reply(self, channel, message):
		await self.client.send_message(channel.rawchannel, message)

	async def reply_in_private(self, user, message):
		await self.client.send_message(user.rawuser, message)

	async def reply_in_notice(self, user, message):
		await self.client.send_message(user.rawuser, message)

