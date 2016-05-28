import socket
import select
import ssl
import traceback
from time import sleep, time
import os
import sys
import atexit
import importlib
import hashlib
import random

if sys.version_info < (3, 0):
	print('Python 3 is required to run the bot.')
	quit()

if not os.path.isfile("config.py"):
	import shutil
	shutil.copyfile("config.py.default", "config.py")
	print("config.py.default copied to config.py")
from config import *
if not configured:
	print("you have not configured the bot, open up config.py to edit settings")
	quit()

print("Loading modules")
mods = {}
mods["common"] = importlib.import_module("common")
print(mods["common"])
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

def SocketSend(socket, message):
	socket.send(message.encode('utf-8'))

def Print(message):
	if encoding != "utf-8":
		message = message.encode(encoding, errors="replace").decode(encoding)
	try:
		print(message)
	except UnicodeEncodeError as e:
		print("Error printing message")
		print("=======ERROR=======\n%s========END========\n" % (traceback.format_exc()))
		#raise e

def Connect():
	global irc
	Print("Connecting to %s..." % (server))
	#irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	#irc.connect((server,6667))
	irc = socket.create_connection((server, port))
	if useSSL:
		irc = ssl.wrap_socket(irc)
	irc.setblocking(0)
	SocketSend(irc, "USER %s %s %s :%s\n" % (botIdent, botNick, botNick, botRealname))
	SocketSend(irc, "NICK %s\n" % (botNick))
	if NickServ:
		SocketSend(irc, "ns identify %s %s\n" % (botAccount, botPassword))
	else:
		for i in channels:
			SocketSend(irc, "JOIN %s\n" % (i))

# These functions are now unused
def ReadPrefs():
		pass

def WritePrefs():
	pass
atexit.register(WritePrefs)

def PrintError(channel = None):
	Print("=======ERROR=======\n%s========END========\n" % (traceback.format_exc()))
	if channel:
		if channel[0] != "#":
			channel = errorchannel
		SocketSend(irc, "PRIVMSG %s :Error printed to console\n" % (channel))
		if errorCode:
			try:
				exec(errorCode)
			except Exception:
				SocketSend(irc, "PRIVMSG %s :We heard you like errors, so we put an error in your error handler so you can error while you catch errors\n" % (channel))
				Print("=======ERROR=======\n%s========END========\n" % (traceback.format_exc()))
	
def Interrupt():
	SocketSend(irc, "QUIT :Keyboard Interrupt\n")
	irc.close()
	quit()

def main():
	socketQueue = b""
	nextSend = 0
	while True:
		try:
			lines = b""
			ready = select.select([irc], [], [], 1.0)
			if ready[0]:
				lines = irc.recv(2040)
		except ssl.SSLWantReadError:
			pass
		except Exception: #socket.error, e:   or   socket.timeout, e:
			PrintError()
			return
		else:
			lines = socketQueue + lines # add on any queue from the last recv
			linesSplit = lines.splitlines()
			socketQueue = b""
			if lines and lines[-1] != ord("\n"):
				socketQueue = linesSplit.pop()
			for line in linesSplit:
				try:
					line = line.decode("utf-8", errors="replace")
					Print("<-- "+line+"\n")
					text = line.split()

					if len(text) > 0:
						#Reply to server pings
						if text[0] == "PING":
							SocketSend(irc, "PONG %s\n" % (text[1]))
						elif text[0] == "ERROR":
							irc.close()
							return #try to reconnect

					if len(text) > 1:
						#Only join channel once identified
						if text[1] == "396":
							for i in channels:
								SocketSend(irc, "JOIN %s\n" % (i))
						#Nickname already in use
						elif text[1] == "433":
							SocketSend(irc, "NICK %s-\n" % (text[3]))
							if NickServ:
								SocketSend(irc, "ns identify %s %s\n" % (botAccount, botPassword))
								SocketSend(irc, "ns ghost %s\n" % (botNick))
								SocketSend(irc, "NICK %s\n" % (botNick))
						elif text[1] == "437":
							SocketSend(irc, "NICK %s-\n" % text[3])
							if NickServ:
								SocketSend(irc, "ns identify %s %s\n" % (botAccount, botPassword))
								SocketSend(irc, "ns release %s\n" % (botNick))
								SocketSend(irc, "NICK %s\n" % (botNick))

					if len(text) > 2:
						#Get channel to reply to
						if text[1] == "PRIVMSG":
							reply = text[2]
							if reply == botNick:
								reply = text[0].split("!")[0].lstrip(":")
						elif text[1] == "NICK" and text[0].split("!")[0][1:] == botNick:
							SocketSend(irc, "NICK %s\n" % (botNick))

					if len(text) >= 4:
						#Parse line in stocks.py
						if len(text):
							Parse(text)

					if len(text) >= 5:
						if text[1] == "MODE" and text[2] == "##powder-bots" and text[3] == "+o" and text[4] == botNick:
							SocketSend(irc, "MODE ##powder-bots -o %s\n" % (botNick))

					#allow modules to do their own text parsing if needed, outside of raw commands
					for mod in mods:
						if hasattr(mods[mod], "Parse"):
							mods[mod].Parse(line, text)
				except SystemExit:
					SocketSend(irc, "QUIT :i'm a potato\n")
					irc.close()
					quit()
				except Exception:
					PrintError(errorchannel or channels[0])
		try:
			#allow modules to have a "tick" function constantly run, for any updates they need
			for mod in mods:
				if hasattr(mods[mod], "AlwaysRun"):
					mods[mod].AlwaysRun(channels[0])

			if messageQueue and time() > nextSend:
				Print("--> %s" % messageQueue[0])
				SocketSend(irc, messageQueue[0])
				messageQueue.pop(0)
				if len(messageQueue) > 3:
					nextSend = time()+.7
			#TODO: maybe proper rate limiting, but this works for now
			"""temp = False
			if len(messageQueue) > 7:
				temp = True
			for i in messageQueue:
				Print("--> %s" % i)
				SocketSend(irc, i)
				if temp:
					sleep(1)
			messageQueue[:] = []"""
		except Exception:
			PrintError(errorchannel or channels[0])

def Parse(text):
	if text[1] == "PRIVMSG":
		channel = text[2]
		username = text[0].split("!")[0].lstrip(":")
		hostmask = text[0].split("!")[1]
		command = text[3].lower().lstrip(":")
		if channel == botNick:
			channel = username
		#if username == "FeynmanStockBot":
		#	return
		if username == "potatorelay" and command.startswith("<") and command.endswith(">") and len(text) > 4:
			text.pop(3)
			command = text[3]

		#some special owner commands that aren't in modules
		if CheckOwner(text[0]):
			if command == "%sreload" % (commandChar):
				if len(text) <= 4:
					SendNotice(username, "No module given")
					return
				modname = text[4]
				if not mods[modname]:
					print(mods["common"])
					return
				print("reloading module "+modname)
				if modname in commands:
					commands[modname] = []
				mods[modname] = importlib.reload(mods[modname])

				output = "Reloaded %s.py" % modname
				if modname == "common":
					globals().update(mods["common"].GetGlobals())
					for othermodname, othermod in mods.items():
						if othermod.__name__[:5] == "mods.":
							mods[othermodname] = importlib.reload(othermod)
							output = output + ", %s.py" % othermodname
				SendMessage(channel, output)
				return
			elif command == "%seval" % (commandChar):
				try:
					command = " ".join(text[4:]).replace("\\n", "\n").replace("\\t", "\t")
					ret = str(eval(command))
				except Exception as e:
					ret = str(type(e))+":"+str(e)
				retlines = ret.splitlines()[:4]
				for line in retlines:
					SendMessage(channel, line)
				return
			elif command == "%sexec" % (commandChar):
				try:
					exec(" ".join(text[4:]))
				except Exception as e:
					SendMessage(channel, str(type(e))+":"+str(e))
				return
			elif command == "%squit" % (commandChar):
				quit()

		#actual commands here
		for mod in commands:
			for i in commands[mod]:
				if command == "%s%s" % (commandChar, i[0]):
					i[1](username, hostmask, channel, text[4:])
					return

ReadPrefs()
while True:
	reconnectAttempts = 0
	try:
		Connect()
		main()
		reconnectAttempts = 0
		sleep(20)
	except KeyboardInterrupt:
		Print("Keyboard inturrupt, bot shut down")
		break
	except Exception:
		PrintError()
		reconnectAttempts = reconnectAttempts + 1
		if reconnectAttempts > 5:
			Print("Too many failed reconnects, quitting")
			break
		Print("A strange error occured, reconnecting in 10 seconds")
		sleep(10)
		pass
