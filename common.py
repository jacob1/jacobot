import inspect
import re
import traceback
import typing

def GetGlobals():
	return globals()

class ShowHelpException(Exception):
	pass

# TODO: make this better, and support both irc / discord
class User(object):
	def __init__(self, message):
		self.nick = message.author.display_name
		self.ident = message.author.name
		self.host = message.author.discriminator
		self.account = message.author.id

	def IsAdmin(self):
		return self.ident == "jacob1" and self.account == "186987207033094146" and self.host == "8633"

command_char = "!!"
class Message(object):
	commandRegex = re.compile(r"^{0}([^ ]+)(?: (.+))?$".format(command_char))
	
	argMatch = re.compile(r"(?:(['\"])(.*?)\1|(\S*))\s*")
	endOfLineArgMatch = re.compile(r"(['\"])(.*?)\1|([\S\s]*?)\s*$")

	def __init__(self, client, message):
		self.sender = User(message)
		self.channel = message.channel
		self.message = message.content
		self.client = client

		self.isCommand = False
		if self.message.startswith(command_char):
			commandParsed = re.search(self.commandRegex, self.message)
			if commandParsed:
				self.isCommand = True
				self.command = commandParsed.group(1)
				self.commandLine = commandParsed.group(2)
				if not self.commandLine:
					self.commandLine = ""

	async def Reply(self, message):
		if not message or len(message) == 0:
			message = "Error: tried sending an empty message"
		await self.client.send_message(self.channel, message)

	def GetArg(self, num, endLine=False):
		if not self.isCommand:
			return None
		
		index = 0
		argNum = 0
		while argNum <= num and index < len(self.commandLine):
			currToEnd = self.commandLine[index:]
			#if endLine and argNum == num:
			#	return currToEnd
			nextArgRegex = self.endOfLineArgMatch if (endLine and argNum == num) else self.argMatch
			nextArgMatch = re.match(nextArgRegex, currToEnd)
			if nextArgMatch:
				nextArg = nextArgMatch.group(2) or nextArgMatch.group(3)
				if argNum == num:
					#print(nextArg)
					return nextArg
				#print(index, nextArgMatch.group(0), index + len(nextArgMatch.group(0)))
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
def command(name):
	
	plugin = ExtractPluginName()
	if plugin not in commands:
		commands[plugin] = []

	def real_command(func):
		def call_func(message):
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
				messagePart = message.GetArg(pos, endLine=sigValue.kind == sigValue.KEYWORD_ONLY)
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

			return func(message, **paramDict)
		call_func.__doc__ = func.__doc__
		func.__sig = inspect.signature(func)
		commands[plugin].append((name, call_func))
		return call_func
	return real_command

