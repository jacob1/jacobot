from datetime import datetime
import json

#https://powdertoy.co.uk/Wiki/api.php?action=query&list=recentchanges&rcprop=timestamp|title|comment|ids|user|loginfo&rclimit=6&format=json

from common import *
RegisterMod(__name__)

stalkingmixer =  False
curronline = False
currgame = None

def AlwaysRun(channel):
	global stalkingmixer, curronline, currgame
	if not stalkingmixer:
		return

	now = datetime.now()
	if now.minute%2 == 0 and now.second == 0:
		info = GetPage("https://mixer.com/api/v1/channels/pilihp64?fields=online,type")
		if not info:
			return
		parsed = json.loads(info)
		if parsed["online"]:
			newgame = parsed["type"]["name"]
			if curronline and newgame == currgame:
				return
			curronline = True
			currgame = parsed["type"]["name"]
			SendMessage("##jacob1", "Pilihp64 is now online playing {0}!".format(currgame))
		else:
			if curronline:
				SendMessage("##jacob1", "Pilihp64 is now offline")
			curronline = False
			currgame = None

@command("stalkmixer", admin=True)
def WatchMixer(message):
	"""(stalkmixer). Toggles whether mixer online status is currently being monitored. Admin only."""
	global stalkingmixer
	stalkingmixer = not stalkingmixer
	message.Reply("Mixer monitoring turned {0}".format("on" if stalkingmixer else "off"))

@command("isstreaming", admin=True)
def NowPlaying(message):
	"""(isstreaming). Gets the current game on pilihp64's mixer stream. Admin only."""
	info = GetPage("https://mixer.com/api/v1/channels/pilihp64?fields=online,type")
	if not info:
		message.Reply("Error: Could not get mixer info")
		return
	parsed = json.loads(info)

	ret = "Pilihp64 is currently {0} playing {1}".format(
	        "online" if parsed["online"] else "offline",
	        parsed["type"]["name"])
	message.Reply(ret)

