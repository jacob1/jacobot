import json

from common import *
RegisterMod(__name__)

@command("nowplaying")
def NowPlaying(message):
	"""(nowplaying). Returns the song currently playing on starcatcher radio."""
	info = GetPage("https://radio.starcatcher.us/getmeta")
	if not info:
		message.Reply("Error: Radio is down")
		return
	parsed = json.loads(info)

	def GetPart(parsed, part):
		if part in parsed:
			return parsed[part]
		return "???"

	ret = "Now playing: \x0309{0}\x03 by \x0303{1}\x03 from \x0310{2}\x03 ({3}), {4}s remaining".format(
		GetPart(parsed, "title"), GetPart(parsed, "artist"), GetPart(parsed, "album"), GetPart(parsed, "date"), int(float(parsed["remaining"])))
	message.Reply(ret)

@command("skip", admin=True)
def Skip(message):
	"""(skip). Skips a song on starcatcher radio."""
	message.Reply(GetPage("https://radio.starcatcher.us/magicalsecret_skip"))

@command("radio")
def Radio(message):
	"""(radio). Gives a link to starcatcher radio."""
	message.Reply("You can listen to starcatcher radio at https://starcatcher.us/Radio")
