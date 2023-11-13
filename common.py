from __future__ import annotations

import asyncio

import config
import inspect
import random
import re
import traceback
import typing_inspect

import permissions
from connection.user import User
from connection.channel import Channel

from typing import TYPE_CHECKING, AnyStr

if TYPE_CHECKING:
	from connection.context import Context


def get_globals():
	return globals()


class ShowHelpException(Exception):
	pass


class BadUserMatch(ValueError):
	def __init__(self, message : str):
		self.message = message


class FailedOptionalException(ValueError):
	def __init__(self, exception : Exception):
		self.exception = exception


class PermissionException(Exception):
	def __init__(self, message : str):
		self.message = message

	def __str__(self):
		return self.message


class NoSuchCommandException(Exception):
	def __init__(self, command_name : str):
		self.message = f"No such command: {command_name}"

	def __str__(self):
		return self.message


class AmbiguousException(Exception):
	def __init__(self, command_name : str, plugins : list[str]):
		plugins_str = ", ".join(plugins)
		self.message = f"Ambiguous command \"{command_name}\", present in these plugins: {plugins_str}"

	def __str__(self):
		return self.message


def get_possible_commands(check_command : str, check_subcommand : str = None, *, plugins : list  = None) -> dict[str, Command]:
	"""Gets commands by name
	@param check_command: Name of command
	@param check_subcommand: Name of subcommand that must exist under command
	@param plugins: optional list of plugins to search in
	@return: dict of commands
	"""
	possible_plugins = {}
	for plugin in filter(lambda p: plugins is None or p in plugins, commands):
		command_list = commands[plugin]
		for cmd in filter(lambda c: c.name == check_command, command_list):
			if check_subcommand is None:
				possible_plugins[plugin] = cmd
				break
			else:
				if cmd.has_subcommands():
					subcmd = cmd.has_subcommand(check_subcommand)
					if subcmd:
						possible_plugins[plugin] = cmd
	return possible_plugins


class CommandParser:
	command_regex : re.Pattern[AnyStr] | None = None
	subcommand_regex: re.Pattern[AnyStr] | None = None
	command_char : str | None = None
	
	argMatch : re.Pattern[AnyStr] | None = None
	endOfLineArgMatch : re.Pattern[AnyStr] | None = None

	def __init__(self, message : str, command_char):
		if CommandParser.command_char is None or CommandParser.command_char != command_char:
			CommandParser._init_regex(command_char)

		self.isCommand = False
		self.command : Command|None = None
		self.subcommand : Command|None = None

		self._message = message
		self._rest = None
		self._command_name = None
		self._subcommand_name = None

	@classmethod
	def _init_regex(cls, command_char):
		cls.command_regex = re.compile(r"^{0}([^ ]+)(?: +(.+))?$".format(command_char))
		cls.subcommand_regex = re.compile(r"^([^ ]+)(?: +(.+))?$")
		cls.command_char = command_char

		cls.argMatch = re.compile(r"(?:(['\"])(.*?)\1|(\S*))\s*")
		cls.endOfLineArgMatch = re.compile(r"(['\"])(.*?)\1|([\S\s]*?)\s*$")

	async def call(self, context : Context):
		# Validate we have permission to run this command
		# Subcommand permission check takes priority, because it's more specific
		ret = None
		if self.subcommand is not None:
			ret, reason = self.subcommand.has_permission(context)
			if ret is False:
				raise PermissionException(reason)

		if not ret:
			ret, reason = self.command.has_permission(context)
			if ret is False:
				raise PermissionException(reason)

		# Call the command
		if self.subcommand is not None:
			await self.subcommand.call(context, self)
		else:
			await self.command.call(context, self)

	def parse(self, context : Context) -> None:
		self.isCommand = False
		#if config.command_char != self.last_command_char:
		#	self.last_command_char = config.command_char
		#	self.command_regex = re.compile(r"^{0}([^ ]+)(?: +(.+))?$".format(config.command_char))
		if self._message.startswith(self.command_char):
			command_parsed = re.search(self.command_regex, self._message)
			if command_parsed:
				self.isCommand = True
				self._command_name = command_parsed.group(1)
				self._subcommand_name = None
				self._rest = command_parsed.group(2)
				if not self._rest:
					self._rest = ""

				self.command = self._get_command(context)
				if self.command and self.command.has_subcommands():
					# Will replace self.command if it's a subcommand
					if not self._check_subcommand():
						raise ShowHelpException()

	def _get_command(self, context : Context) -> Command:
		is_plugin_name = self._command_name in commands
		possible_commands = get_possible_commands(self._command_name)

		# Check for edge case where there was one match, but it's actually incorrect and the user was manually specifying a plugin
		if len(possible_commands) == 1 and is_plugin_name and self._command_name not in possible_commands:
			ret, cmd = self._check_specified_plugin(self._command_name)
			if ret:
				return cmd
		# Command present in multiple plugins
		if len(possible_commands) != 1:
			# "command" is a plugin name
			if is_plugin_name:
				ret, cmd = self._check_specified_plugin(self._command_name)
				if ret:
					return cmd

			# Delete commands for which the user has no permission
			for (command_name, cmd) in possible_commands.items():
				if cmd.has_permission(context) is False:
					del possible_commands[command_name]

		# If plugin and command share a name, and it's ambiguous, then that command has precedence
		if len(possible_commands) > 1 and is_plugin_name and self._command_name in possible_commands:
			return possible_commands[self._command_name]

		if len(possible_commands) == 1:
			return list(possible_commands.values())[0]
		elif len(possible_commands) > 1:
			raise AmbiguousException(self._command_name, list(possible_commands.keys()))
		else:
			raise NoSuchCommandException(self._command_name)

	def _check_specified_plugin(self, plugin : str) -> tuple[bool, Command | None]:
		"""Check if the user manually specified the plugin name"""
		parsed = re.search(self.subcommand_regex, self._rest)
		if parsed:
			command_name = parsed.group(1)
			rest = parsed.group(2)
			possible_commands = get_possible_commands(command_name, plugins=[plugin])
			if possible_commands:
				assert(len(possible_commands) == 1) # Always True
				self._command_name = command_name
				self._rest = rest if rest is not None else ""
				return True, list(possible_commands.values())[0]
		return False, None

	def _check_subcommand(self):
		"""Check which subcommand the user called"""
		subcommand_parsed = re.search(self.subcommand_regex, self._rest)
		if subcommand_parsed:
			subcommand_name = subcommand_parsed.group(1)
			rest = subcommand_parsed.group(2)
			if self.command.has_subcommand(subcommand_name):
				self._subcommand_name = subcommand_name
				self._rest = rest if rest is not None else ""
				self.subcommand = self.command.get_subcommand(subcommand_name)
				return True
		return False

	def get_arg(self, num : int, end_line : bool = False) -> str|None:
		if not self.isCommand:
			return None
		
		index = 0
		arg_num = 0
		while arg_num <= num and index < len(self._rest):
			curr_to_end = self._rest[index:]
			next_arg_regex = self.endOfLineArgMatch if (end_line and arg_num == num) else self.argMatch
			next_arg_match = re.match(next_arg_regex, curr_to_end)
			if next_arg_match:
				next_arg = next_arg_match.group(2) or next_arg_match.group(3)
				if arg_num == num:
					return next_arg
				index = index + len(next_arg_match.group(0))
			else:
				return None

			arg_num = arg_num + 1
		return None

# Used in command decorators to enforce a regex match on an argument
class RegexArg:
	def __init__(self, regex):
		self.regex = re.compile(regex)

	def __call__(self, arg):
		if not re.fullmatch(self.regex, arg):
			raise ValueError("Regex doesn't match")
		return arg


class ExactMatchArg:
	def __init__(self, str_match):
		self.str_match = str_match

	def __call__(self, arg):
		if self.str_match != arg:
			raise ValueError("String doesn't match")
		return arg


def ExtractPluginName() -> str:
	tb = traceback.extract_stack(limit=3)
	plugin_part = re.search(r"plugins[/\\](.*)\.py", tb[0][0])
	if not plugin_part:
		raise Exception("@command can only be called inside of plugins in the plugins/ folder")
	return plugin_part.group(1)


class Command:
	def __init__(self, name : str, func, elevated : bool = False, owner : bool = False, group_name : str = None):
		self._name = name
		self._func = func
		self._sig = inspect.signature(func)
		self._param_keys = list(self._sig.parameters.keys())[1:] # Skip context parameter
		self._param_values = list(self._sig.parameters.values())[1:]
		self._elevated = elevated
		# For elevated commands, grant access to the appropriate group
		if elevated:
			group_name = group_name if group_name else "admin"
			add_command_permission_to_group(name, group_name)
		self._owner = owner
		self._subcommands : dict[str,Command]|None = None

	def has_permission(self, context : Context) -> tuple[bool | None, str | None]:
		is_owner = context.sender.is_owner()
		if not is_owner:
			global_perms = permissions.check_global_enabled(context)
			if not global_perms:
				return False, None #"Commands are disabled on this server"
			if self._owner:
				return False, "You are not an owner"

		channel_perms = permissions.check_channel_enabled(context)
		if not channel_perms:
			return False, None #"Commands are disabled in this channel"
		if not is_owner:
			reason = permissions.check_command_permission(context, self._name)
			if reason and reason.flag is False:
				return False, "You are not allowed to use this command"
			if reason and reason.flag is True:
				return True, None
			if not reason and self._elevated:
				return False, "You do not have permission to use this command"
		return None, None

	def get_help(self) -> str:
		return self._func.__doc__

	@staticmethod
	def _init_arg(sig_value : inspect.Parameter, message_part : str, context : Context, optional : bool):
		try:
			annotation = sig_value.annotation if not optional else sig_value.annotation.__args__[0]
			if annotation is User:
				found, user = context.server.find_user(context, message_part, requested_for=context.sender)
				if not found:
					if user is None:
						raise BadUserMatch(f"User \"{message_part}\" not found")
					else:
						possible_users = []
						for possible_user in user:
							possible_users.append(f"{possible_user.name}#{possible_user.discriminator}")
						raise BadUserMatch("Ambiguous user, could be " + ", ".join(possible_users))
				return user
			if annotation is Channel:
				found, channel = context.server.find_channel(context, message_part, requested_for=context.sender)
				if not found:
					if channel is None:
						raise BadUserMatch(f"Channel \"{message_part}\" not found")
					else:
						possible_channels = []
						for possible_channel in channel:
							possible_channels.append(f"#{possible_channel.name}")
						raise BadUserMatch("Ambiguous channel, could be " + ", ".join(possible_channels))
				return channel
			return annotation(message_part)
		except ValueError as e:
			if not optional:
				raise e
			raise FailedOptionalException(e)

	@staticmethod
	def _is_optional(sig_value : inspect.Parameter) -> bool:
		# if typing.get_origin(sig_value.annotation) is typing.Union and type(None) in typing.get_args(sig_value.annotation):
		# Probably typing.Optional. Above commented out line may work in the future, but neither logic seems to work
		#  if from __future__ import annotations is at the top of the module. Python docs mentions it will try to
		#  un-stringize the annotations, maybe that causes it?
		if typing_inspect.is_union_type(sig_value.annotation):
			return True
		return False

	def _check_parameters(self, context : Context, command_parser : CommandParser, param_dict : dict[str, any], sig_pos : int, parse_pos : int) -> None:
		param_name = self._param_keys[sig_pos]
		param_value = self._param_values[sig_pos]
		is_optional = self._is_optional(param_value)
		message_part = command_parser.get_arg(parse_pos, end_line=param_value.kind == param_value.KEYWORD_ONLY)
		if message_part is None and not is_optional:
			raise ValueError("Not enough arguments")

		parameter = None
		try:
			# Parse the argument into an object
			if message_part is not None or not is_optional:
				parameter = self._init_arg(param_value, message_part, context, is_optional)
			failed_optional = False
		except FailedOptionalException:
			failed_optional = True

		# If there's more parameters, try to handle them
		if sig_pos + 1 < len(self._param_keys):
			exception = None
			parse_pos_check = [0] if failed_optional else [1, 0]
			for i in parse_pos_check:
				try:
					self._check_parameters(context, command_parser, param_dict, sig_pos + 1, parse_pos + i)
					exception = None
					break
				except ValueError as e:
					if exception is None or not is_optional:
						exception = e
					if not is_optional:
						break
				parameter = None
			if exception:
				raise exception
		elif sig_pos + 1 == len(self._param_keys):
			# Very last parameter is optional, but we still have more unused parts of the message
			# Force raise an error so that help text is shown on how to use the final optional
			if parameter is None and message_part:
				raise ValueError()

		param_dict[param_name] = parameter

	async def call(self, context : Context, command_parser : CommandParser):
		# Parse arguments, if there are any
		param_dict : dict[str, any] = {}
		if len(self._param_keys):
			try:
				self._check_parameters(context, command_parser, param_dict, 0, 0)
			except BadUserMatch as e:
				raise e
			except ValueError as e:
				raise ShowHelpException()

		await self._func(context, **param_dict)

	@property
	def name(self) -> str:
		return self._name

	@property
	def command(self):
		return self._func

	def has_subcommands(self) -> bool:
		return self._subcommands is not None

	def has_subcommand(self, name : str) -> bool:
		return self._subcommands is not None and name in self._subcommands

	def get_subcommand(self, name : str) -> Command|None:
		if self._subcommands is None:
			return None
		return self._subcommands[name]

	def add_subcommand(self, name : str, cmd : Command) -> None:
		if self._subcommands is None:
			self._subcommands = {}
		if name in self._subcommands:
			raise Exception(f"Subcommand {name} for {self._name} already exists")
		self._subcommands[name] = cmd


commands : dict[str, list[Command]] = {}
def command(name : str, elevated : bool = False, owner : bool = False, group_name : str = None):
	"""Decorator which registers a command

	@param name: Command name
	@param elevated:   True if special permissions are required to run this command
	@param owner:      True if only config-defined owners can run this command
	@param group_name: Group name which grants access to this command (if elevated). If unspecified, defaults to the "admin" group
	"""

	def real_command(func):
		plugin = ExtractPluginName()
		if plugin not in commands:
			commands[plugin] = []

		command_obj = Command(name, func, elevated, owner, group_name)
		commands[plugin].append(command_obj)
		return None

	return real_command

def subcommand(parent_name : str, name : str, elevated : bool = False, group_name : str = None):
	"""Decorator which registers a subcommand. Inherits most properties from parent command

	@param parent_name: Parent command's name
	@param name:        Subcommand name
	@param elevated:    True if special permissions are required to run this subcommand
	@param group_name   Group name which grants access to this subcommand (if elevated). If unspecified, defaults to the "admin" group
	"""

	def real_command(func):
		plugin = ExtractPluginName()
		if plugin not in commands:
			commands[plugin] = []

		parent_command_search = get_possible_commands(parent_name, plugins=[plugin])
		if plugin not in parent_command_search:
			raise Exception(f"Parent command {parent_name} not found")

		cmd = parent_command_search[plugin]
		subcommand_obj = Command(f"{parent_name}.{name}", func, elevated, owner=False, group_name=group_name)
		cmd.add_subcommand(name, subcommand_obj)
		return None

	return real_command

def add_permission_to_group(permission : str, group_name : str) -> None:
	"""Add permission to group. All members of this group will automatically have this permission.
	Meant to be run on startup only to initialize group permissions."""
	permissions.add_permission_to_group(permission, group_name)

def add_command_permission_to_group(command_name : str, group_name : str) -> None:
	"""Add command permission to group. All members of this group will automatically have this permission.
	Meant to be run on startup only to initialize group permissions."""
	permissions.add_command_permission_to_group(command_name, group_name)

def ScheduleInterval(func, interval : int, initial_delay : int, random_delay : int) -> None:
	"""Schedule a function to run with a certain frequency. Will ensure there is 'interval' seconds between invocations,
	so it may drift over time depending on how long the callback takes to execute"""
	if random_delay >= interval:
		raise Exception("random_delay must be less than interval")
	loop = asyncio.get_event_loop()
	def callback():
		if random_delay:
			asyncio.sleep(random.randint(0, random_delay))
		func()
		loop.call_later(interval, callback)
	loop.call_later(initial_delay, callback)

def ScheduleFixed(func, interval : int, initial_delay : int = 0, random_delay : int = 0) -> None:
	"""Schedule a function to run with a fixed delay. Will continue being called at the interval regardless of how
	long it takes the callback to run"""
	if random_delay >= interval:
		raise Exception("random_delay must be less than interval")
	loop = asyncio.get_event_loop()
	def callback(scheduled_time):
		if random_delay:
			loop.call_later(random.randint(0, random_delay), func)
		else:
			loop.call_soon(func)
		loop.call_at(scheduled_time + interval, callback, scheduled_time + interval)
	loop.call_at(loop.time() + initial_delay, callback, loop.time() + initial_delay)

# Schedule permission writer
ScheduleFixed(permissions.write_all_permissions, 60, 0)

def FlushAllData() -> None:
	permissions.write_all_permissions()