from __future__ import annotations

import asyncio
from typing import Any, Tuple

import discord

from event import *
from connection.channel import *
from connection.context import *
from connection.user import *

# Generic Server class, subclasses (DiscordServer and IrcServer) will implement connection and send out events
class Server:
	@abstractmethod
	def find_user(self, context : Context, search_str : str, *, requested_for : User = None) -> Tuple[bool, User|None|set]:
		pass

	@abstractmethod
	def find_channel(self, context : Context, search_str : str, *, requested_for : User = None, exact_match : bool = False) -> Tuple[bool, Channel|None|set]:
		pass

class DiscordServer(Server):

	def __init__(self, name : str, token : str, owners : list[dict[str, Any]], guilds : list[dict[str, Any]], event_handler):
		self._name = name
		self._token = token
		self._owners = owners
		self._guilds = guilds
		self._event_handler = event_handler

		intents = discord.Intents.default()
		intents.members = True
		intents.typing = False
		intents.message_content = True
		self.client = discord.Client(intents=intents)

	@property
	def client(self) -> discord.client.Client:
		return self._client

	@client.setter
	def client(self, client : discord.client.Client):
		self._client = client
		client.event(self.on_message)

	@property
	def name(self) -> str:
		return self._name

	async def on_message(self, message):
		if message.author == self.client.user:
			return

		sender = DiscordUser(message.author, self)

		if isinstance(message.channel, discord.DMChannel):
			receiver = DiscordUser(message.channel, self)
			server_name = "discord"
		elif isinstance(message.channel, discord.TextChannel):
			receiver = DiscordChannel(message.channel)
			server_id = message.channel.guild.id
			server_name = None
			for guild in self._guilds:
				if guild["id"] == server_id:
					server_name = guild["name"]
					break
			if not server_name:
				return
		# Probably a group dm, ignore for now
		else:
			return

		context = Context("discord", server_name, self, sender, receiver)
		await self._event_handler(MessageEvent(context, message.content))

	async def connect(self):
		await self._client.start(self._token)
		self._token = None # Clear for security reasons

	def find_user(self, server_name : str, search_str : str, *, requested_for : DiscordUser = None) -> Tuple[bool, DiscordUser|None|set]:
		all_matches = set()
		server_matches = set()
		search_str_lower = search_str.lower()
		for server in self.client.guilds:
			# Only allow users to see other users present in their own discords
			if requested_for:
				found = False
				for s_member in server.members:
					if s_member.id == requested_for.account_name:
						found = True
						break
				if not found:
					continue
			# Search server for matching members
			for s_member in server.members:
				if (s_member.name.lower().startswith(search_str_lower)
						or s_member.display_name.lower().startswith(search_str_lower)
						or f"{s_member.display_name.lower()}#{s_member.discriminator}" == search_str_lower):
					all_matches.add(s_member)
					if server_name == server.name:
						server_matches.add(s_member)
		if len(server_matches) == 1:
			return True, DiscordUser(server_matches.pop(), self)
		if len(server_matches) == 0 and len(all_matches) == 1:
			return True, DiscordUser(all_matches.pop(), self)
		if len(server_matches) == 0 and len(all_matches) == 0:
			return False, None
		return False, set([DiscordUser(u, self) for u in all_matches.union(server_matches)])

	def find_channel(self, server_name : str, search_str : str, *, requested_for : User | None = None, exact_match : bool = False) -> Tuple[bool, DiscordChannel|None|set]:
		matches = set()
		search_str_lower = search_str.lower()
		for server in self.client.guilds:
			if server_name != server.name:
				continue

			# Search server for matching channels
			for channel in server.channels:
				if (exact_match and channel.name.lower() == search_str_lower or
						not exact_match and channel.name.lower().startswith(search_str_lower)):
					# Verify the requesting user can see this channel
					for member in channel.members:
						if not requested_for or member.id == requested_for.account_name:
							matches.add(channel)
							break
		if len(matches) == 1:
			return True, DiscordChannel(matches.pop())
		if len(matches) == 0:
			return False, None
		return False, set([DiscordChannel(c) for c in matches])

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

	def __init__(self, event_handler, *, name, host, port, ssl, nick, ident, owners, channels,
				 account_name = None, account_password = None):
		self._name = name
		self.host = host
		self.port = port
		self.ssl = ssl
		self.nick = nick
		self.ident = ident
		self.account_name = account_name
		self.account_password = account_password
		self.owners = owners
		self.channels = channels

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
		for channel in self.channels:
			self.writer.write(f"JOIN {channel}\n".encode("utf-8"))

		# https://docs.python.org/3.5/library/asyncio-eventloop.html
		# https://docs.python.org/3.5/library/asyncio-protocol.html#asyncio-transport
		# https://docs.python.org/3.5/library/asyncio-stream.html#asyncio-register-socket-streams    <-----

	@property
	def name(self):
		return self._name

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
		print(f"--> {message.strip()}")
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

	@staticmethod
	def parse_prefix(prefix):
		(nick, identhost) = prefix.split("!")
		if nick[0] == ":":
			nick = nick[1:]

		(ident, host) = prefix.split("@")
		return nick, ident.split("!")[1], host


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

		context = Context("irc", self.name, self, sender, receiver)
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

	def find_user(self, context : Context, search_str : str, *, requested_for : User = None) -> Tuple[bool, IrcUser|None|set]:
		if search_str == "jacob1":
			return True, IrcUser("jacob1", "jacob1", "Powder/Developer/jacob1", self)
		if search_str == "jacob1_":
			return True, IrcUser("jacob1_", "~jacob1", "Powder/Developer/jacob1", self)
		elif search_str == "mooo":
			return True, IrcUser("mooo", "~jacob1", "Powder/Developer/jacob1", self)
		elif search_str == "Liver_K":
			return True, IrcUser("Liver_K", "Liver", "user/Liver", self)
		elif search_str == "Liver-K":
			return True, IrcUser("Liver-K", "Liver", "user/Liver", self)
		return False, None
		#raise Exception("find_user not implemented for IrcServer")

	def find_channel(self, context : Context, search_str : str, *, requested_for : User = None, exact_match : bool = False) -> Tuple[bool, IrcChannel|None|set]:
		matches = set()
		search_str_lower = search_str.lower()

		# Search server for matching channels
		for channel in self.channels:
			if channel.lower().startswith(search_str_lower):
				matches.add(channel)
		if len(matches) == 1:
			return True, IrcChannel(matches.pop(), self)
		if len(matches) == 0:
			return False, None
		return False, set([IrcChannel(c, self) for c in matches])
