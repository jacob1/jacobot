import asyncio
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

		if isinstance(message.channel, discord.DMChannel):
			receiver = DiscordUser(message.channel)
		elif isinstance(message.channel, discord.TextChannel):
			receiver = DiscordChannel(message.channel)
		# Probably a group dm, ignore for now
		else:
			return

		context = Context(self, sender, receiver)
		await self.event_handler(MessageEvent(context, message.content))

	async def connect(self):
		await self._client.start(self.token)
		self.token = None # Clear for security reasons

# Small class to store reader and writer during connection class reloads
class IrcClient:

	def __init__(self, reader, writer):
		self.reader = reader
		self.writer = writer

# Decorator for events
def irchandler(event_name):
	def irc_event_handler(func):
		async def call_irc_event_handler(self, prefix, event, args):
			await func(self, prefix, event, args)

		irc_event_handlers[event_name] = call_irc_event_handler

	return irc_event_handler
irc_event_handlers = {}

class IrcServer(Server):

	def __init__(self, event_handler, *, host, port, ssl, nick, ident, account_name = None, account_password = None):
		self.host = host
		self.port = port
		self.ssl = ssl
		self.nick = nick
		self.ident = ident
		self.account_name = account_name
		self.account_password = account_password

		self.event_handler = event_handler
		self.reconnect = False

		self.reader = None
		self.writer = None

	async def connect(self):
		self.reader, self.writer = await asyncio.open_connection(self.host, self.port, ssl = self.ssl)
		self.writer.write(f"USER {self.ident} {self.nick} {self.nick} :jacobot rewrite\n".encode("utf-8"))
		self.writer.write(f"NICK {self.nick}\n".encode("utf-8"))
		if self.account_name:
			self.writer.write(f"ns identify {self.account_name} {self.account_password}\n".encode("utf-8"))
		self.writer.write("JOIN ##jacob1\n".encode("utf-8"))

		# https://docs.python.org/3.5/library/asyncio-eventloop.html
		# https://docs.python.org/3.5/library/asyncio-protocol.html#asyncio-transport
		# https://docs.python.org/3.5/library/asyncio-stream.html#asyncio-register-socket-streams    <-----

	@property
	def client(self):
		return IrcClient(self.reader, self.writer)

	@client.setter
	def client(self, client):
		if client is None:
			self.reader = None
		else:
			self.reader = client.reader
			self.writer = client.writer

	def raw_send(self, message):
		self.writer.write(f"{message}\n".encode("utf-8"))

	def parse_raw_line(self, line):
		if line[0] == ":":
			# ERROR :Closing Link: new.starcatcher.us (Ping timeout: 252 seconds)
			#print("Unexpected raw irc message: " + str(line))
			#return None, None, None

			prefix_pos = line.find(" ")
			if prefix_pos < 0:
				print("Invalid raw irc message: " + line)
				return None, None, None
			prefix = line[:prefix_pos]
		else:
			prefix = None
			prefix_pos = -1

		event_pos = line.find(" ", prefix_pos + 1)
		if event_pos < 0:
			print("Invalid raw irc message: " + line)
			return None, None, None
		event = line[prefix_pos + 1:event_pos]

		args = []
		arg_pos = event_pos
		next_arg_pos = line.find(" ", arg_pos + 1)
		while next_arg_pos >= 0:
			if line[arg_pos + 1] == ":":
				args.append(line[arg_pos + 2:])
				break
			args.append(line[arg_pos + 1:next_arg_pos])
			arg_pos = next_arg_pos
			next_arg_pos = line.find(" ", arg_pos + 1)
		else:
			if line[arg_pos + 1] == ":":
				arg_pos = arg_pos + 1
			args.append(line[arg_pos + 1:])
		# strip \r\n
		args[-1] = args[-1][:-2]

		return prefix, event, args

	def parse_prefix(self, prefix):
		(nick, identhost) = prefix.split("!")
		(ident, host) = prefix.split("@")
		return nick, ident, host


	@irchandler("ERROR")
	async def server_error_handler(self, prefix, event, args):
		self.reconnect = True

	@irchandler("PING")
	async def server_ping_handler(self, prefix, event, args):
		self.raw_send(f"PONG {args[0]}")

	@irchandler("PRIVMSG")
	async def privmsg_handler(self, prefix, event, args):
		(nick, ident, host) = self.parse_prefix(prefix)
		sender = IrcUser(nick, ident, host, self)

		channel_name = args[0]
		if channel_name[0] == "#":
			receiver = IrcChannel(channel_name, self)
		else:
			receiver = IrcUser(channel_name, None, None, self)

		context = Context(self, sender, receiver)
		await self.event_handler(MessageEvent(context, args[1]))

	async def main_loop(self):
		while self.reader:
			line = await self.reader.readline()
			line = line.decode("utf-8")
			print(f"<-- {line.strip()}")
			if len(line) == 0:
				break

			(prefix, event, args) = self.parse_raw_line(line)

			for event_name, handler in irc_event_handlers.items():
				if event_name == event:
					await handler(self, prefix, event, args)

			if self.reconnect:
				await self.connect()
		print("Main IRC Loop has exited")
