from datetime import datetime
import json
import re
import socket
import urllib

from common import *
RegisterMod(__name__)

frequency = 60

def SendToCrackbot(channel, message):
        crackbot = socket.create_connection(("localhost", "9876"))
        crackbot.send("msg {0} {1}\n".format(channel, message).encode('utf-8'))
        crackbot.close()

def CheckWiki(message):
	global frequency

	lastrc = GetData(__name__, "lastrc") #7346
	if not lastrc:
		lastrc = 0

	try:
		info = GetPage("https://powdertoy.co.uk/Wiki/api.php?action=query&list=recentchanges&rcprop=timestamp|title|comment|ids|user|loginfo&rclimit=6&format=json")
	except IOError:
		return
	if not info:
		return
	parsed = json.loads(info)
	changes = parsed["query"]["recentchanges"]
	for change in changes[::-1]:
		if change["rcid"] > lastrc:
			frequency = 10
			#SendMessage("##jacob1", "Found wiki change on page " + change["title"])
			StoreData(__name__, "lastrc", change["rcid"])

			title = change["title"]
			showlink = True

			if change["type"] == "edit":
				msg = "edited page"
			elif change["type"] == "new":
				msg = "created page"
			elif change["type"] == "log":
				if change["logtype"] == "move":
					msg = "moved page from " + change["title"] + " to"
					title = change["logparams"]["target_title"]
				elif change["logtype"] == "delete":
					msg = "deleted page"
					showlink = False
				else:
					msg = "did log action " + change["logtype"] + " on page"
			else:
				msg = "did action " + change["type"] + " on page"
			msg = "\x0305{0}\x03 {1} \x0302{2}\x03".format(change["user"], msg, title)
			if change["comment"]:
				msg = msg + ": " + change["comment"]

			if showlink:
				if change["old_revid"]:
					urlparts = { "title" : title, "curid" : change["pageid"], "diff" : change["revid"], "oldid" : change["old_revid"] }
				else:
					urlparts = { "title" : title }
				msg = msg + " - https://powdertoy.co.uk/Wiki/index.php?" + urllib.parse.urlencode(urlparts)

			if message:
				message.Reply(msg)
			else:
				if title and re.search("/..$", title):
					#SendToCrackbot("#powder-info", msg)
					SendMessage("#powder-info", msg)
				else:
					SendToCrackbot("#powder", msg)
				#SendMessage("##jacob1", msg)
			

def AlwaysRun(channel):
	global frequency

	now = datetime.now()
	seconds = now.minute * 60 + now.second
	if seconds % frequency == 0:
		if frequency < 60:
			frequency = frequency + 1
		CheckWiki(None)

@command("wikitest")
def Wikitest(message):
	CheckWiki(message)

