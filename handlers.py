import os
import sys
import traceback
import importlib
from datetime import datetime
import base64
from typing import List

class ReloadedModuleException(Exception):
	pass

mods = {}
def LoadMods():
	print("Loading modules")

	mods["config"] = importlib.import_module("config")
	globals().update(mods["config"].GetGlobals())
	mods["common"] = importlib.import_module("common")
	globals().update(mods["common"].GetGlobals())

	for i in os.listdir("mods"):
		if os.path.isfile(os.path.join("mods", i)) and i[-3:] == ".py" and i[:-3] not in disabledPlugins:
			try:
				print("Loading {} ...".format(i))
				mods[i[:-3]] = importlib.import_module("mods.{0}".format(i[:-3]))
			except Exception:
				print("Error loading {}".format(i))
				print(traceback.format_exc())
				pass
	print("Done loading modules")

def JoinChans():
	"""Joins all channels, usually called after authentication is complete"""
	for i in channels:
		Send("JOIN %s\n" % (i))

lastSecond = 0
def Tick():
	global lastSecond
	now = datetime.now()
	if now.second == lastSecond:
		return
	lastSecond = now.second
	
	#allow modules to have a "tick" function constantly run, for any updates they need
	for mod in mods:
		if hasattr(mods[mod], "AlwaysRun"):
			mods[mod].AlwaysRun(channels[0])
	if now.second == 30:
		mods["common"].WriteAllData()

def LoadIrcHooks():
	"""Register hooks for various IRC events and numerics"""

	doing_sasl_registration = False
	needs_regain_command = None
	regain_attempts = 0

	@hook("396")
	def event_hosthidden(prefix : str, command : str, args : List[str]):
		"""Joins IRC channels once we have identified and had a cloak set"""
		JoinChans()

	@hook("433")
	@hook("437")
	def event_nicknameinuse(prefix : str, command : str, args : List[str]):
		"""Nickname is in use (433) or unavailable (437), use temporary nick to logon then later regain the nick"""
		nonlocal doing_sasl_registration
		nonlocal regain_attempts
		nonlocal needs_regain_command

		if not botPassword:
			return

		# While doing registration, append a dash to the nick so we can try again, and queue a ns regain for later
		if doing_sasl_registration:
			attempted_nick = args[1]
			Send(f"NICK {attempted_nick}-\n")
			needs_regain_command = "ghost" if command == "433" else "regain"
		# Once identified, try nicking to our rightful nick
		# The first attempt seems to fail because the old connection isn't killed fast enough
		else:
			if regain_attempts < 3:
				Send(f"NICK {botNick}\n")
			regain_attempts = regain_attempts + 1

	server_caps = {}
	enabled_caps = {}
	@hook("CAP")
	def command_cap(prefix : str, command : str, args : List[str]):
		nonlocal server_caps
		nonlocal enabled_caps
		nonlocal doing_sasl_registration
		nonlocal needs_regain_command
		nonlocal regain_attempts

		cap_type = args[1]
		if cap_type == "LS":
			# Reset variables on reconnection
			doing_sasl_registration = False
			needs_regain_command = None
			regain_attempts = 0

			for cap in args[-1].split():
				if cap.find("=") != -1:
					(key, value) = cap.split("=", 1)
					server_caps[key] = value
				else:
					server_caps[cap] = True

			# Multiline cap, continue on
			if args[2] == "*":
				return

			requested_caps = []
			if sasl:
				requested_sasl_type = "PLAIN" if not certfp_certfile else "EXTERNAL"
				if server_caps["sasl"] and requested_sasl_type in server_caps["sasl"].upper().split(","):
					requested_caps.append("sasl")
					doing_sasl_registration = True
				else:
					print("SASL PLAIN not supported on this server, but sasl was requested in the bot config. Aborting.")
					sys.exit(1)

			if requested_caps:
				Send("CAP REQ :" + " ".join(requested_caps) + "\n")
			else:
				Send("CAP END\n")
		elif cap_type == "ACK":
			for cap in args[-1].split():
				if cap[0] == "-":
					enabled_caps[cap[1:]] = False
				else:
					enabled_caps[cap] = True
					if cap == "sasl":
						requested_sasl_type = "PLAIN" if not certfp_certfile else "EXTERNAL"
						Send(f"AUTHENTICATE {requested_sasl_type}\n")

		elif cap_type == "NAK" or cap_type == "DEL":
			for cap in args[-1].split():
				enabled_caps[cap] = False
			if not enabled_caps["sasl"]:
				doing_sasl_registration = False

	if sasl:
		@hook("AUTHENTICATE")
		def command_authenticate(prefix : str, command : str, args : List[str]):
			if args[0] == "+":
				requested_sasl_type = "PLAIN" if not certfp_certfile else "EXTERNAL"
				if requested_sasl_type == "PLAIN":
					account = botAccount.encode("utf-8")
					password = botPassword.encode("utf-8")
					auth_token = base64.b64encode(b"\0".join((account, account, password))).decode("utf-8")
					Send("AUTHENTICATE " + auth_token + "\n")
				else:
					Send("AUTHENTICATE +\n")

		@hook("903")
		def event_saslsuccess(prefix : str, command : str, args : List[str]):
			nonlocal doing_sasl_registration
			nonlocal needs_regain_command

			Send("CAP END\n")
			# Now that we are identified, ghost / regain our old connection if necessary
			if needs_regain_command:
				Send(f"ns {needs_regain_command} {botNick}\n")
				Send(f"NICK {botNick}\n")
			JoinChans()
			doing_sasl_registration = False

		@hook("902")
		@hook("904")
		@hook("905")
		@hook("906")
		@hook("908")
		def event_saslfailed(prefix : str, command : str, args : List[str]):
			print("SASL Failed, aborting")
			sys.exit(1)

def HandleLine(line : str, text : str):
	# The following chunks parse the host/irc server prefix, the command/numeric, and the arguments
	prefix, command, args = None, None, None
	pos = -1
	if line[0] == ":":
		pos = line.find(" ")
		prefix = line[:pos]

	next_pos = line.find(" ", pos + 1)
	if next_pos > 0:
		command = line[pos + 1:next_pos].upper()

		rest = line[next_pos + 1:]
		colon_split = rest.split(":", 1)
		args = []
		args.extend(colon_split[0].rstrip().split(" "))
		if len(colon_split) > 1:
			args.append(colon_split[1])

	# Check if there are any hooks registered for this command / numeric
	if command in hooks:
		for hook in hooks[command]:
			hook(prefix, command, args)

	# Leaving legacy junk in place for now, jacobot is getting rewritten later anyway
	if len(text) >= 4:
		if len(text) and text[1] == "PRIVMSG":
			SetRateLimiting(True)
			HandlePrivmsg(line, text)
	if len(text) >= 5:
		if text[1] == "MODE" and text[2] == "#powder-bots" and text[3] == "+o" and text[4] == botNick:
			Send("MODE #powder-bots -o %s\n" % (botNick))

	#allow modules to do their own text parsing if needed, outside of raw commands
	for mod in mods:
		if hasattr(mods[mod], "Parse"):
			mods[mod].Parse(line, text)

def HandlePrivmsg(line, text):
	message = Message(line)
	SetCurrentChannel(message.replyChannel)
	if not message.isCommand:
		return

	#some special owner commands that aren't in modules
	if CheckOwner(text[0]):
		if message.command == "reload":
			if len(text) <= 4:
				SendNotice(username, "No module given")
				return
			modname = text[4]
			if modname == "config":
				del sys.modules["config"]
				mods["config"] = importlib.import_module("config")
				globals().update(mods["config"].GetGlobals())
				mods["common"].adminHostmasks = mods["config"].adminHostmasks
				mods["common"].ownerHostmasks = mods["config"].ownerHostmasks
				raise ReloadedModuleException({"message":"Reloading {0}.py".format(modname), "module":modname, "channel":message.channel})
			elif modname == "handlers" or modname == "common":
				raise ReloadedModuleException({"message":"Reloading {0}.py".format(modname), "module":modname, "channel":message.channel})
			elif modname not in mods:
				message.Reply("No such module")
				return

			if modname in commands:
				commands[modname] = []
			mods[modname] = importlib.reload(mods[modname])

			message.Reply("Reloaded {0}.py".format(modname))
			return
		elif message.command == "load":
			if len(text) <= 4:
				SendNotice(username, "No module given")
				return
			modname = text[4]
			if modname in mods:
				message.Reply("Module already loaded")
				return
			try:
				mods[modname] = importlib.import_module("mods.{0}".format(modname))
			except ModuleNotFoundError:
				message.Reply("Module not found: {0}.py".format(modname))
				return
			message.Reply("Loaded {0}.py".format(modname))
			return
		elif message.command == "unload":
			if len(text) <= 4:
				SendNotice(username, "No module given")
				return
			modname = text[4]
			if modname not in mods:
				message.Reply("Module not loaded")
				return
			if modname in commands:
				del commands[modname]
			del mods[modname]
			del sys.modules["mods.{0}".format(modname)]
			message.Reply("Unloaded {0}.py".format(modname))
			return
		elif message.command == "eval":
			try:
				command = " ".join(text[4:]).replace("\\n", "\n").replace("\\t", "\t")
				ret = str(eval(command))
			except Exception as e:
				ret = str(type(e))+":"+str(e)
			retlines = ret.splitlines()[:4]
			for line in retlines:
				message.Reply(line)
			return
		elif message.command == "exec":
			try:
				exec(" ".join(text[4:]))
			except Exception as e:
				message.Reply(str(type(e))+":"+str(e))
			return
		elif message.command == "quit":
			quit()
		elif message.command == "writedata":
			WriteAllData(force=True)
		elif message.command == "cleardata":
			initialized = {}

	#actual commands here
	for mod in commands:
		for i in commands[mod]:
			if message.command == i[0]:
				try:
					i[1](message)
				except mods["common"].ShowHelpException:
					if i[1].__doc__:
						message.Reply("Usage: %s" % (i[1].__doc__))
				return

