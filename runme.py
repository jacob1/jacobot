import socket
import select
import ssl
import traceback
from time import sleep, time
import os
import sys
import atexit
import importlib

if sys.version_info < (3, 0):
	print('Python 3 is required to run the bot.')
	quit()

if not os.path.isfile("config.py"):
	import shutil
	shutil.copyfile("config.py.default", "config.py")
	print("config.py.default copied to config.py")

try:
	config = importlib.import_module("config")
	globals().update(config.GetGlobals())
except Exception:
	print("Error loading config.py, cannot start bot")
	print(traceback.format_exc())
	sys.exit(1)

if not configured:
	print("you have not configured the bot, open up config.py to edit settings")
	sys.exit(0)

try:
	import common
except Exception:
	print("Error loading common.py, cannot start bot")
	print(traceback.format_exc())
	sys.exit(1)

try:
	import handlers
	handlers.LoadMods()
except Exception:
	print("Error loading handlers.py, cannot start bot")
	print(traceback.format_exc())
	sys.exit(1)

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

def PrintError():
	Print("=======ERROR=======\n{0}========END========\n".format(traceback.format_exc()))
	currentChannel = common.GetCurrentChannel()
	if currentChannel:
		SocketSend(irc, "PRIVMSG {0} :Error printed to console\n".format(currentChannel))
		if errorCode:
			try:
				exec(errorCode)
			except Exception:
				SocketSend(irc, "PRIVMSG {0} :We heard you like errors, so we put an error in your error handler so you can error while you catch errors\n".format(currentChannel))
				Print("=======ERROR=======\n{0}========END========\n".format(traceback.format_exc()))
	common.SetCurrentChannel(None)
	
def Interrupt():
	SocketSend(irc, "QUIT :Keyboard Interrupt\n")
	irc.close()
	quit()

def main():
	global config
	global common

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
					
					if text:
						#Reply to server pings
						if text[0] == "PING":
							SocketSend(irc, "PONG %s\n" % (text[1]))
						elif text[0] == "ERROR":
							irc.close()
							return

					handlers.HandleLine(line, text)
					common.SetCurrentChannel(None)
				except handlers.ReloadedModuleException as e:
					reloadedModule = e.args[0]["module"]
					if reloadedModule == "common":
						common = importlib.reload(common)
						globals().update(common.GetGlobals())
						common.SetCurrentChannel(None)
						common.SetRateLimiting(True)
						sys.modules["common"] = common
					elif reloadedModule == "config":
						config = importlib.reload(config)
						globals().update(config.GetGlobals())
					elif reloadedModule == "handlers":
						print("Reloading handlers")
						try:
							importlib.reload(sys.modules["handlers"])
							handlers.LoadMods()
							SocketSend(irc, "PRIVMSG {0} :Reloaded handlers.py\n".format(e.args[0]["channel"]))
						except Exception:
							common.SetCurrentChannel(e.args[0]["channel"])
							PrintError()
							common.SetCurrentChannel(None)
						else:
							print("Reloaded")
				except SystemExit:
					SocketSend(irc, "QUIT :i'm a potato\n")
					irc.close()
					quit()
				except Exception:
					PrintError()
		try:
			handlers.Tick()
			common.SetCurrentChannel(None)
			
			if common.messageQueue and (time() > nextSend or not common.DoRateLimiting()):
				if not common.DoRateLimiting():
					while common.messageQueue:
						Print("--> %s" % common.messageQueue[0])
						SocketSend(irc, common.messageQueue[0])
						common.messageQueue.pop(0)
				elif time() > nextSend:
					Print("--> %s" % common.messageQueue[0])
					SocketSend(irc, common.messageQueue[0])
					common.messageQueue.pop(0)
					if len(common.messageQueue) > 3:
						nextSend = time()+.7
		except Exception:
			PrintError()

ReadPrefs()
reconnectAttempts = 0
while True:
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
