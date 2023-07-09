import time
import datetime
import config

from common import *
RegisterMod(__name__)

botMessage = r"^:(?:(potato|mc|creative)relay!~mcrelay@user/jacob1/bot/potatorelay) PRIVMSG #powder-mc :"
def Parse(raw, text):
	match = re.match(botMessage + r"<([^>]+)\x0F> (.+)$", raw)
	connection = False
	if not match:
		match = re.match(botMessage + r"\x0314\[([^ ]+) ((?:dis)?connected)\]", raw)
		connection = True

	if match:
		server = "unknown server"
		if match.group(1) == "mc":
			server = "survival"
		elif match.group(1) == "creative":
			server = "creative"

		username = match.group(2)
		message = match.group(3)
		if not connection:
			StoreData(__name__, username, {"server":server,"message":message,"time":time.time()})
		else:
			StoreData(__name__, f"connection-{username}", {"server":server,"type":message,"time":time.time()})

@command("seenmc", minArgs=1)
def SeenMc(message):
	"""(seenmc <user>). Prints the last server, message, and time <user> was seen at."""
	if not message.GetArg(0):
		raise ShowHelpException()
	user = message.GetArg(0)
	lastSeen = GetData(__name__, user)
	lastConnection = GetData(__name__, f"connection-{user}")
	if not lastSeen and not lastConnection:
		message.Reply("{0} has not been seen on Minecraft".format(user))
	else:
		if lastSeen:
			timemsg = datetime.datetime.utcfromtimestamp(lastSeen["time"]).strftime("%a %b %d %Y at %I:%M:%S%p UTC")
			message.Reply("{0} was last seen on {1} on {2}: {3}".format(user, lastSeen["server"], timemsg, lastSeen["message"]))
		if lastConnection and (not lastSeen or lastConnection["time"] - 600 > lastSeen["time"]):
			timemsg = datetime.datetime.utcfromtimestamp(lastConnection["time"]).strftime("%a %b %d %Y at %I:%M:%S%p UTC")
			connectionType = "disconnected from" if lastConnection["type"] == "disconnected" else "connected to"
			message.Reply("{0} last {1} {2} on {3}".format(user, connectionType, lastConnection["server"], timemsg))
