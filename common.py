import inspect
import re
import traceback
import typing

def get_globals():
	return globals()

class ShowHelpException(Exception):
	pass

class PermissionException(Exception):
	pass

command_char = "!!"
class CommandParser:
	commandRegex = re.compile(r"^{0}([^ ]+)(?: (.+))?$".format(command_char))
	
	argMatch = re.compile(r"(?:(['\"])(.*?)\1|(\S*))\s*")
	endOfLineArgMatch = re.compile(r"(['\"])(.*?)\1|([\S\s]*?)\s*$")

	def __init__(self, message):
		self.message = message#.content

		self.isCommand = False
		if self.message.startswith(command_char):
			commandParsed = re.search(self.commandRegex, self.message)
			if commandParsed:
				self.isCommand = True
				self.command = commandParsed.group(1)
				self.commandLine = commandParsed.group(2)
				if not self.commandLine:
					self.commandLine = ""

	def get_arg(self, num, endLine=False):
		if not self.isCommand:
			return None
		
		index = 0
		argNum = 0
		while argNum <= num and index < len(self.commandLine):
			currToEnd = self.commandLine[index:]
			nextArgRegex = self.endOfLineArgMatch if (endLine and argNum == num) else self.argMatch
			nextArgMatch = re.match(nextArgRegex, currToEnd)
			if nextArgMatch:
				nextArg = nextArgMatch.group(2) or nextArgMatch.group(3)
				if argNum == num:
					return nextArg
				index = index + len(nextArgMatch.group(0))
			else:
				return None

			argNum = argNum + 1
		return None

# Used in command decorators to enforce a regex match on an argument
class RegexArg():
	def __init__(self, regex):
		self.regex = re.compile(regex)

	def __call__(self, arg):
		if not re.fullmatch(self.regex, arg):
			raise ValueError("Regex doesn't match")
		return arg

def ExtractPluginName():
	tb = traceback.extract_stack(limit=3)
	pluginPart = re.search(r"plugins[/\\](.*)\.py", tb[0][0])
	if not pluginPart:
		raise Exception("@command can only be called inside of plugins in the plugins/ folder")
	return pluginPart.group(1)

commands = {}
def command(name, owner = False):
	
	plugin = ExtractPluginName()
	if plugin not in commands:
		commands[plugin] = []

	def real_command(func):
		def call_func(context, command_parser):
			if owner and not context.sender.is_owner():
				raise PermissionException()

			# keyword Dict to be passed into function
			paramDict = {}
			pos = -1
			# TODO: only one optional in a row properly supported right now
			prevOptional = None
			for sigName, sigValue in func.__sig.parameters.items():
				if pos == -1:
					pos = 0
					continue

				optional = False
				# Probably typing.Optional
				if type(sigValue.annotation) == type(typing.Union):
					optional = True

				# Extract a word from the message. Show help if this argument doesn't exist
				messagePart = command_parser.get_arg(pos, endLine=sigValue.kind == sigValue.KEYWORD_ONLY)
				if messagePart == None:
					if optional:
						paramDict[sigName] = None
						continue
					raise ShowHelpException()

				parameter = None
				try:
					parameter = sigValue.annotation(messagePart) if not optional else sigValue.annotation.__args__[0](messagePart)
				except ValueError:
					if optional:
						paramDict[sigName] = None
						continue
					elif prevOptional:
						try:
							parameter = prevOptional(messagePart)
						except ValueError:
							raise ShowHelpException()
					raise ShowHelpException()
				paramDict[sigName] = parameter
				pos = pos + 1
				prevOptional = sigValue.annotation if optional else None

			return func(context, **paramDict)
		call_func.__doc__ = func.__doc__
		func.__sig = inspect.signature(func)
		commands[plugin].append((name, call_func))
		return call_func
	return real_command

