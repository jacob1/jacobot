import time
import datetime
import config

from common import *
RegisterMod(__name__)

def Parse(raw, text):
	match = re.match("^:(.[^!]+)![^@]+@[^ ]+ PRIVMSG (#[^ ]+) :(.+)", raw)
	if match:
		username = match.group(1)
		channel = match.group(2)
		message = match.group(3)
		# TODO: settings per mod (a config file to handle what not to save here)
		if channel != config.errorChannel and channel == "#powder-mc":
			server = False
			if username == "mcrelay" or username == "mcrelay2":
				server = "survival"
			elif username == "creativerelay" or username == "creativerelay2":
				server = "creative"
			if server:
				messageMatch = re.match("^<(.*(?=>))> (.*)", message)
				if messageMatch:
					user = messageMatch.group(1)
					msg = messageMatch.group(2)
					StoreData(__name__, user, {"server":server,"message":msg,"time":time.time()})

@command("seenmc", minArgs=1)
def SeenMc(message):
	"""(seenmc <user>). Prints the last server, message, and time <user> was seen at."""
	if not message.GetArg(0):
		raise ShowHelpException()
	if message.GetArg(0) == "impostor":
		timemsg = datetime.datetime.utcfromtimestamp(time.time()).strftime("%a %b %d %Y at %I:%M:%S%p UTC")
		message.Reply("{0} was last seen on {1}: !!seenmc impostor".format(message.nick, timemsg)) # You are the impostor
	else:
		user = message.GetArg(0)
		lastSeen = GetData(__name__, user)
		if not lastSeen:
			message.Reply("{0} has not been seen".format(user))
		else:
			timemsg = datetime.datetime.utcfromtimestamp(lastSeen["time"]).strftime("%a %b %d %Y at %I:%M:%S%p UTC")
			message.Reply("{0} was last seen on {1} on {2}: {3}".format(user, lastSeen["server"], timemsg, lastSeen["message"]))

