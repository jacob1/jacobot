import socket
import select
import ssl
import traceback
import time
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

if certfp_certfile and not sasl:
	print("To use CertFP, you must enable sasl")

try:
	common = importlib.import_module("common")
except Exception:
	print("Error loading common.py, cannot start bot")
	print(traceback.format_exc())
	sys.exit(1)

try:
	handler = importlib.import_module("handlers")
	handler.LoadMods()
	handler.LoadIrcHooks()
except Exception:
	print("Error loading handlers.py, cannot start bot")
	print(traceback.format_exc())
	sys.exit(1)

def SocketSend(socket, message):
	blocked_strings = ["AUTHENTICATE", "ns identify"]
	did_block = False
	for blocked_string in blocked_strings:
		if message[:len(blocked_string)] == blocked_string:
			Print(f"--> {blocked_string} [REDACTED]")
			did_block = True
			break
	if not did_block:
		Print("--> %s" % message.rstrip())
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
		context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

		# Enable certificate validation
		context.verify_mode = ssl.CERT_REQUIRED
		context.check_hostname = True
		context.load_default_certs()

		# Disable insecure protocols / options
		context.options |= ssl.OP_NO_SSLv2
		context.options |= ssl.OP_NO_SSLv3
		context.options |= ssl.OP_NO_TLSv1
		context.options |= ssl.OP_NO_TLSv1_1
		context.options |= ssl.OP_NO_COMPRESSION
		context.options |= ssl.OP_NO_TICKET

		# For certfp option
		if certfp_certfile:
			context.load_cert_chain(certfp_certfile, certfp_keyfile, password="")

		irc = context.wrap_socket(irc, server_hostname=server)

	irc.setblocking(0)

	if sasl:
		if not botPassword:
			print("Fatal: sasl requested but botPassword is not set")
			sys.exit(1)
		SocketSend(irc, "CAP LS 302\n")

	SocketSend(irc, "USER %s %s %s :%s\n" % (botIdent, botNick, botNick, botRealname))
	SocketSend(irc, "NICK %s\n" % (botNick))
	if botPassword and not sasl:
		SocketSend(irc, "ns identify %s %s\n" % (botAccount, botPassword))
	elif not botPassword:
		handler.JoinChans()

def WriteAllData():
	common.WriteAllData(force=True)
atexit.register(WriteAllData)

def PrintError():
	Print("=======ERROR=======\n{0}========END========\n".format(traceback.format_exc()))
	currentChannel = common.GetCurrentChannel()
	if currentChannel:
		SocketSend(irc, "PRIVMSG {0} :Error printed to console\n".format(currentChannel))
	if errorCode:
		try:
			exec(errorCode)
		except Exception:
			SocketSend(irc, "PRIVMSG {0} :We heard you like errors, so we put an error in your error handler so you can error while you catch errors\n".format(errorChannel))
			Print("=======ERROR=======\n{0}========END========\n".format(traceback.format_exc()))
	common.SetCurrentChannel(None)
	
def Interrupt():
	SocketSend(irc, "QUIT :Keyboard Interrupt\n")
	irc.close()
	quit()

def main():
	global config
	global common
	global handler

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
					Print("<-- "+line)
					text = line.split()
					
					if text:
						#Reply to server pings
						if text[0] == "PING":
							SocketSend(irc, "PONG %s\n" % (text[1]))
						elif text[0] == "ERROR":
							irc.close()
							return

					handler.HandleLine(line, text)
					common.SetCurrentChannel(None)
				except handler.ReloadedModuleException as e:
					reloadedModule = e.args[0]["module"]
					if reloadedModule == "config":
						globals().update(handler.mods["config"].GetGlobals())
						SocketSend(irc, "PRIVMSG {0} :Reloaded config.py\n".format(e.args[0]["channel"]))
					elif reloadedModule == "handlers":
						try:
							common.WriteAllData(force=True)
							for modname, mod in handler.mods.items():
								if mod.__name__ in sys.modules:
									del sys.modules[mod.__name__]
							del sys.modules["handlers"]
							handler = importlib.import_module("handlers")
							common = importlib.import_module("common")
							handler.LoadMods()
							handler.LoadIrcHooks()
						except Exception:
							common.SetCurrentChannel(e.args[0]["channel"])
							PrintError()
							common.SetCurrentChannel(None)
						else:
							globals().update(handler.mods["common"].GetGlobals())
							common.SetCurrentChannel(None)
							common.SetRateLimiting(True)
							SocketSend(irc, "PRIVMSG {0} :Reloaded handlers.py, common.py, and all plugins\n".format(e.args[0]["channel"]))
					elif reloadedModule == "common":
						common.WriteAllData(force=True)
						for modname, mod in handler.mods.items():
							if mod.__name__ in sys.modules:
								del sys.modules[mod.__name__]
						common = importlib.import_module("common")
						common.SetCurrentChannel(None)
						common.SetRateLimiting(True)
						handler.LoadMods()
						handler.LoadIrcHooks()
						SocketSend(irc, "PRIVMSG {0} :Reloaded common.py and all plugins\n".format(e.args[0]["channel"]))
				except SystemExit:
					SocketSend(irc, "QUIT :i'm a potato\n")
					irc.close()
					quit()
				except Exception:
					PrintError()
		try:
			handler.Tick()
			common.SetCurrentChannel(None)
			
			if common.messageQueue and (time.time() > nextSend or not common.DoRateLimiting()):
				if not common.DoRateLimiting():
					while common.messageQueue:
						SocketSend(irc, common.messageQueue[0])
						common.messageQueue.pop(0)
				elif time.time() > nextSend:
					SocketSend(irc, common.messageQueue[0])
					common.messageQueue.pop(0)
					if len(common.messageQueue) > 3:
						nextSend = time.time()+.7
		except Exception:
			PrintError()

reconnectAttempts = 0
while True:
	try:
		Connect()
		main()
		reconnectAttempts = 0
		time.sleep(20)
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
		time.sleep(10)
		pass
