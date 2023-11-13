from connection.channel import IrcChannel, DiscordChannel

class MockIrcChannel(IrcChannel):
    def __init__(self, name : str):
        super().__init__(name, None)

    def is_owner(self):
        return False

    async def reply(self, message):
        print(f"T--> {self._name} --> {message}")


class MockDiscordChannel(DiscordChannel):
    def __init__(self, name : str):
        super().__init__(None)
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def topic(self):
        return None

    async def reply(self, message):
        print(f"T--> {self._name} --> {message}")