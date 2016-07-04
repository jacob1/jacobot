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
def Seen(username, hostmask, channel, text):
	"""(seen [<channel>] <user>). Prints the last message and time <user> was seen at."""
	chan = channel
	if text[0].startswith("#"):
		if len(text) == 1:
			raise ShowHelpException()
		chan = text.pop(0)
	lastSeen = GetData(__name__, "{0}.{1}".format(chan, text[0]))
	if not lastSeen:
		SendMessage(channel, "{0} has not been seen in {1}".format(text[0], chan))
	else:
		timemsg = datetime.datetime.utcfromtimestamp(lastSeen["time"]).strftime("%a %b %d %Y at %I:%M:%S%p UTC")
		SendMessage(channel, "{0} was last seen in {1} on {2}: {3}".format(text[0], chan, timemsg, lastSeen["message"]))

