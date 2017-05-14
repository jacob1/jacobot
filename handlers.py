import os
import sys
import traceback
import importlib
from datetime import datetime

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

def HandleLine(line, text):
	if len(text) > 1:
		#Only join channel once identified
		if text[1] == "396":
			for i in channels:
				Send("JOIN %s\n" % (i))
		#Nickname already in use
		elif text[1] == "433":
			Send("NICK %s-\n" % (text[3]))
			if NickServ:
				Send("ns identify %s %s\n" % (botAccount, botPassword))
				Send("ns ghost %s\n" % (botNick))
				Send("NICK %s\n" % (botNick))
		elif text[1] == "437":
			Send("NICK %s-\n" % text[3])
			if NickServ:
				Send("ns identify %s %s\n" % (botAccount, botPassword))
				Send("ns release %s\n" % (botNick))
				Send("NICK %s\n" % (botNick))

	if len(text) > 2:
		#Get channel to reply to
		if text[1] == "PRIVMSG":
			reply = text[2]
			if reply == botNick:
				reply = text[0].split("!")[0].lstrip(":")
		elif text[1] == "NICK" and text[0].split("!")[0][1:] == botNick:
			Send("NICK %s\n" % (botNick))

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

