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
		if channel != config.errorChannel and channel != "#powder-info":
			StoreData(__name__, "{0}.{1}".format(channel, username), {"message":message,"time":time.time()})
	
@command("seen", minArgs=1)
def Seen(message):
	"""(seen [<channel>] <user>). Prints the last message and time <user> was seen at."""
	chan = message.channel
	user = message.GetArg(0)
	if user.startswith("#"):
		if not message.GetArg(1):
			raise ShowHelpException()
		chan = user
		user = message.GetArg(1)
	lastSeen = GetData(__name__, "{0}.{1}".format(chan, user))
	if not lastSeen:
		message.Reply("{0} has not been seen in {1}".format(user, chan))
	else:
		timemsg = datetime.datetime.utcfromtimestamp(lastSeen["time"]).strftime("%a %b %d %Y at %I:%M:%S%p UTC")
		message.Reply("{0} was last seen in {1} on {2}: {3}".format(user, chan, timemsg, lastSeen["message"]))

