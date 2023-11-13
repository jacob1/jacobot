import importlib
from unittest import IsolatedAsyncioTestCase

from common import CommandParser, commands, ShowHelpException, AmbiguousException, NoSuchCommandException
from test.mock_connection.mock_context import MockContext
from test.mock_connection.mock_user import MockIrcUser
from test.mock_connection.mock_channel import MockIrcChannel


class TestCommandParsing(IsolatedAsyncioTestCase):
	@classmethod
	def setUpClass(cls):
		sender = MockIrcUser("fakeuser", "~fakeuser", "user/fakeuser")
		receiver = MockIrcChannel("##fakechannel")
		cls.context = MockContext("irc", "mockserver", None, sender, receiver)

		importlib.import_module("test.plugins.fake_test_plugin")
		importlib.import_module("test.plugins.fake_test_plugin_2")
		importlib.import_module("test.plugins.fake_test_plugin_3")

	async def check_command_output(self, message: str, expected_output: str):
		"""Check if parsing and running a command with the given message produces the expected output"""
		command_parser = CommandParser(f"!!{message}", "!!")
		command_parser.parse(self.context)

		await command_parser.call(self.context)
		self.assertEqual(expected_output, self.context.last_reply)

	async def check_command_error(self, message: str):
		"""Check if parsing and running a command with the given message raises a ShowHelpException"""
		command_parser = CommandParser(f"!!{message}", "!!")
		command_parser.parse(self.context)

		with self.assertRaises(ShowHelpException):
			await command_parser.call(self.context)

	async def check_command_ambiguous(self, message: str, command_name : str, plugins : list[str]):
		"""Check if parsing and running a command with the given message raises a specific AmbiguousException"""
		command_parser = CommandParser(f"!!{message}", "!!")
		with self.assertRaisesRegex(AmbiguousException, str(AmbiguousException(command_name, plugins))):
			command_parser.parse(self.context)

	async def check_command_doesnt_exist(self, message: str, command_name : str):
		"""Check if parsing and running a command with the given message raises a specific NoSuchCommandException"""
		command_parser = CommandParser(f"!!{message}", "!!")
		with self.assertRaisesRegex(NoSuchCommandException, str(NoSuchCommandException(command_name))):
			command_parser.parse(self.context)


	async def test_basic_ping(self):
		"""Test basic command parsing for ping command"""
		command_parser = CommandParser("!!ping a 1", "!!")
		command_parser.parse(self.context)
		correct_ping_command = next(cmd for cmd in commands["fake_test_plugin"] if cmd.name == "ping")
		self.assertEqual(correct_ping_command, command_parser.command)
		self.assertEqual("!!", command_parser.command_char)
		self.assertEqual("ping", command_parser.command.name)

	async def test_fake_commands(self):
		"""Test commands that don't exist"""
		await self.check_command_doesnt_exist("fake", "fake")
		await self.check_command_doesnt_exist("fake_test_plugin_3 fake", "fake")

	async def test_ambiguous_commands(self):
		"""Test ambiguous commands and manual plugin specification"""
		await self.check_command_ambiguous("test", "test", ["fake_test_plugin", "fake_test_plugin_2", "fake_test_plugin_3"])
		await self.check_command_output("fake_test_plugin test a 1", "a, 1")
		await self.check_command_output("fake_test_plugin_2 test 1 a", "1, a")
		await self.check_command_output("fake_test_plugin_3 test 1 1", "1, 1")

	async def test_command_same_as_plugin_name_becomes_default(self):
		"""Both fake_test_plugin and fake_test_plugin2 have a command fake_test_plugin.
		Ensure we can call both, and that "fake_test_plugin" by itself is automatically defaulted to the version from fake_test_plugin"""
		await self.check_command_output("fake_test_plugin fake_test_plugin", "Plugin 1")
		await self.check_command_output("fake_test_plugin_2 fake_test_plugin", "Plugin 2")
		await self.check_command_output("fake_test_plugin", "Plugin 1")

	async def test_command_with_other_plugins_name(self):
		"""Plugin fake_test_plugin has command fake_test_plugin_2"""
		await self.check_command_output("fake_test_plugin_2", "Plugin 1 reply")
		await self.check_command_output("fake_test_plugin fake_test_plugin_2", "Plugin 1 reply")

	async def test_optionals(self):
		"""General optionals testing"""
		await self.check_command_output("optionals testing 2", "testing, 2, None, None")
		await self.check_command_output("optionals testing 2str", "testing, None, 2str, None")
		await self.check_command_output("optionals testing 2 3", "testing, 2, 3, None")
		await self.check_command_output("optionals testing 2 3 4", "testing, 2, 3, 4")

	async def test_optionals2(self):
		"""Make sure optionals fail when none match, test multiple optionals in a row"""
		await self.check_command_error("optionals2 testing 2")
		await self.check_command_error("optionals2 testing 2str")
		await self.check_command_error("optionals2 testing 2 3")
		await self.check_command_error("optionals2 testing 2 3 4")
		await self.check_command_output("optionals2 2", "2, None, None, None")
		await self.check_command_output("optionals2 3 4 5", "3, 4, 5, None")
		await self.check_command_output("optionals2 2 3", "2, 3, None, None")
		await self.check_command_output("optionals2 2 3 moo", "2, 3, moo, None")
		await self.check_command_output("optionals2 2 3 moo 4", "2, 3, moo, 4")

	async def test_optionals3(self):
		"""Test multiple optionals in a row"""
		await self.check_command_output("optionals3 testing 2", "None, testing, 2")
		await self.check_command_output("optionals3 3 2", "3, None, 2")
		await self.check_command_output("optionals3 4", "None, None, 4")

	async def test_optionals4(self):
		"""Test ExactMatchArg and RegexArg"""
		await self.check_command_output("optionals4 4", "None, None, None, 4")
		await self.check_command_output("optionals4 --arg1 4", "--arg1, None, None, 4")
		await self.check_command_output("optionals4 --arg2 4", "None, --arg2, None, 4")
		await self.check_command_output("optionals4 --arg1 --arg2 4", "--arg1, --arg2, None, 4")
		await self.check_command_output("optionals4 --arg2 --arg1 4", "None, --arg2, --arg1, 4")
		await self.check_command_output("optionals4 --arg2 --arg1 --arg3 4", "None, --arg2, --arg1, --arg3")
		await self.check_command_output("optionals4 --random1 --random2", "None, None, None, --random1")

	async def test_optionals5(self):
		"""Make sure that required arguments aren't accidentally treated as optionals"""
		await self.check_command_error("optionals5 1 str 2 3")
