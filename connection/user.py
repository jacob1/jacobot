from abc import ABC, abstractmethod

class User(ABC):
	@abstractmethod
	async def reply(self, message):
		pass

	@abstractmethod
	async def reply_in_notice(self, message):
		pass

class DiscordUser(User):

	def __init__(self, user):
		self.user = user

	# TODO: proper permissions, not stored in this file
	def is_owner(self):
		return self.user.name == "jacob1" and self.user.id == 186987207033094146 and self.user.discriminator == "8633"

	@property
	def rawuser(self):
		return self.user

	@property
	def nick(self):
		return self.user.display_name

	@property
	def account_name(self):
		return self.user.name

	async def reply(self, message):
		await self.user.send(message)

	async def reply_in_notice(self, message):
		await self.user.send(message)

class IrcUser(User):

	# TODO: support +v/+o modes, maybe with some kind of "role" abstraction similar to discord
	def __init__(self, nick, ident, host, server):
		self._nick = nick
		self._ident = ident
		self._host = host
		self._server = server

	def is_owner(self):
		return self._host == "Powder/Developer/lykos.jacob1"

	@property
	def nick(self):
		return self._nick

	# TODO
	@property
	def account_name(self):
		return None

	async def reply(self, message):
		self._server.raw_send(f"PRIVMSG {self.nick} :{message}\n")

	async def reply_in_notice(self, message):
		self._server.raw_send(f"NOTICE {self.nick} :{message}\n")
