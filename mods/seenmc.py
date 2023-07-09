import time
import datetime
import config

from common import *
RegisterMod(__name__)

def Parse(raw, text):
	match = re.match(r"^:(?:(potato|mc|creative)relay!~mcrelay@user/jacob1/bot/potatorelay) PRIVMSG #powder-mc :<([^>]+)\x0F> (.+)$", raw)
	if match:
		server = "unknown server"
		if match.group(1) == "mc":
			server = "survival"
		elif match.group(1) == "creative":
			server = "creative"
		StoreData(__name__, match.group(2), {"server":server,"message":match.group(3),"time":time.time()})

@command("seenmc", minArgs=1)
def SeenMc(message):
	"""(seenmc <user>). Prints the last server, message, and time <user> was seen at."""
	if not message.GetArg(0):
		raise ShowHelpException()
	user = message.GetArg(0)
	lastSeen = GetData(__name__, user)
	if not lastSeen:
		message.Reply("{0} has not been seen".format(user))
	else:
		timemsg = datetime.datetime.utcfromtimestamp(lastSeen["time"]).strftime("%a %b %d %Y at %I:%M:%S%p UTC")
		message.Reply("{0} was last seen on {1} on {2}: {3}".format(user, lastSeen["server"], timemsg, lastSeen["message"]))
