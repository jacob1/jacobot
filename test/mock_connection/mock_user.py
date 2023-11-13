from connection.user import IrcUser, DiscordUser

class MockIrcUser(IrcUser):
    def __init__(self, nick, ident, host):
        super().__init__(nick, ident, host, None)

    def is_owner(self):
        return False

    async def reply(self, message):
        print(f"T--> {self._nick} --> {message}")

    async def reply_in_notice(self, message):
        print(f"T--> [{self._nick}] --> {message}")


class MockDiscordUser(DiscordUser):
    def __init__(self, display_name : str, user_id : int):
        # TODO fake properties for user
        super().__init__(None, None)
        self._display_name = display_name
        self._user_id = user_id

    def is_owner(self):
        return False

    @property
    def rawuser(self):
        return None

    @property
    def nick(self):
        return self._display_name

    @property
    def account_name(self):
        return self._user_id

    async def reply(self, message):
        print(f"T--> {self._display_name} --> {message}")

    async def reply_in_notice(self, message):
        print(f"T--> {self._display_name} --> {message}")
