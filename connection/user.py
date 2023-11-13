from abc import ABC, abstractmethod

class User(ABC):
	@abstractmethod
	async def reply(self, message):
		pass

	@abstractmethod
	async def reply_in_notice(self, message):
		pass

	@abstractmethod
	def is_owner(self):
		pass

	@property
	@abstractmethod
	def nick(self) -> str:
		pass

	@property
	@abstractmethod
	def account_name(self) -> str:
		pass

class DiscordUser(User):

	def __init__(self, user, server):
		self._user = user
		self._server = server

	def __str__(self):
		return self._user.display_name

	def is_owner(self):
		for owner in self._server._owners:
			if self._user.id == owner["id"]:
				return True
		return False

	@property
	def rawuser(self):
		return self._user

	@property
	def nick(self):
		return self._user.display_name

	@property
	def account_name(self) -> str:
		return self._user.id

	async def reply(self, message):
		print(f"--> [{self.nick}] {message.strip()}")
		await self._user.send(message)

	async def reply_in_notice(self, message):
		print(f"--> [{self.nick}] {message.strip()}")
		await self._user.send(message)

class IrcUser(User):

	# TODO: support +v/+o modes, maybe with some kind of "role" abstraction similar to discord
	def __init__(self, nick, ident, host, server):
		self._nick = nick
		self._ident = ident
		self._host = host
		self._server = server

	def __str__(self):
		return self._nick

	def is_owner(self):
		return self.account_name in self._server.owners

	@property
	def nick(self):
		return self._nick

	# TODO
	@property
	def account_name(self) -> str:
		return f"{self._ident}@{self._host}"

	async def reply(self, message):
		self._server.raw_send(f"PRIVMSG {self.nick} :{message}\n")

	async def reply_in_notice(self, message):
		self._server.raw_send(f"NOTICE {self.nick} :{message}\n")
