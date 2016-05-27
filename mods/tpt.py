import html.parser
import json
import time
import re
from common import *
from datetime import datetime
from time import sleep
RegisterMod(__name__)

ipbans = {}
def Parse(raw, text):
	match = re.match("^:(?:StewieGriffinSub|PowderBot)!(?:Stewie|jacksonmj3|bagels)@turing.jacksonmj.co.uk PRIVMSG #powder-info :New registration: ([\w_-]+)\. https?:\/\/tpt\.io\/@([\w\_-]+) \[([0-9.]+)\] ?$", raw)
	if match:
		#SendMessage("#powder-info", "test: %s %s %s" % (match.group(1), match.group(2), match.group(3)))
		ip = match.group(3)
		for address in ipbans:
			if ip.startswith(address):
				BanUser(match.group(1), "1", "p", "Automatic ban: this IP address has been blacklisted")
				SendMessage("#powder-info", "Automatic ban: this IP address has been blacklisted")
		torfile = open("torlist.txt")
		torips = torfile.readlines()
		torfile.close()
		torips = map(lambda ip: ip.strip(), torips)
		if ip in torips:
			SendMessage("#powder-info", "Warning: This account was registered using TOR")
	#match = re.match("^:(?:StewieGriffinSub|PowderBot)!(?:Stewie|jacksonmj3|bagels)@turing.jacksonmj.co.uk PRIVMSG #powder-saves :Warning: LCRY, Percentage: ([0-9.]+), https?:\/\/tpt.io\/~([0-9]+)$", raw)
													#New: 'Deut compressor' by HugInfinity (0 comments, score 1, 1 bump); http://tpt.io/~1973995
	match = re.match("^:(?:StewieGriffinSub|PowderBot)!(?:Stewie|jacksonmj3|bagels)@turing.jacksonmj.co.uk PRIVMSG #powder-saves :New: \u000302'(.+?)'\u000F by\u000305 ([\w_-]+)\u000314 \(.*?\)\u000F; https?:\/\/tpt.io\/~([0-9]+)$", raw)
	if match:
		saveID = match.group(3)
		name = match.group(1)
		if "cow" in name.lower():
			if not PromotionLevel(saveID, -1):
				SendMessage("+#powder-saves", "Error demoting save ID %s" % (saveID))
			else:
				SendMessage("+#powder-saves", "Demoted save ID %s" % (saveID))
		"""info = GetSaveInfo(saveID)
		if info:
			sleep(1)
			elementCount = {}
			for element in info["ElementCount"]:
				elementCount[element["Name"]] = int(element["Count"])
			if "LCRY" in elementCount and elementCount["LCRY"] > 75000:
				LCRYpercent = float(elementCount["LCRY"]) / (sum(elementCount.values()))
				if LCRYpercent > .9:
					#SendMessage("jacob1", "demoting save ID %s, %s" % (saveID, LCRYpercent))
					if not PromotionLevel(saveID, -1):
						SendMessage("+#powder-saves", "Error demoting save ID %s" % (saveID))
					else:
						SendMessage("+#powder-saves", "Demoted save ID %s" % (saveID))"""

seenReports = {}
def AlwaysRun(channel):
	global seenReports
	now = datetime.now()
	if now.minute == 30 and now.second ==  0:
		reportlist = ReportsList()
		if reportlist == None:
			SendMessage("#powder-info", "Error fetching reports")
			return
		reportlistunseen = [report for report in reportlist if seenReports.get(report[1]) != int(report[0])]
		for report in reportlistunseen:
			if seenReports.get(report[1]) and int(report[0]) > int(seenReports.get(report[1])):
				report = (int(report[0]) - int(seenReports.get(report[1])), report[1], report[2])
		if len(reportlist):
			SendMessage("#powder-info", u"There are \u0002%s unread reports\u0002: " % (len(reportlist)) + ", ".join(["http://tpt.io/~%s#Reports %s" % (report[1], report[0]) for report in reportlist]))
			PrintReportList("#powder-info", reportlistunseen)
		seenReports = {}
		for report in reportlist:
			seenReports[report[1]] = int(report[0])

		#if len(reportlist):
		#	SendMessage("#powder-info", "Report list: " + ", ".join(["http://tpt.io/~%s#Reports %s" % (report[1], report[0]) for report in reportlist]))
		#else:
		#	SendMessage("#powder-info", "Test: No reports")

		convolist = GetConvoList()
		for convo in convolist:
			SendMessage("jacob1", "Conversation: {0} by {1} ({2} messages)".format(convo["Subject"], convo["MostRecent"], convo["MessageCount"]))
		sleep(1)

#Generic useful functions
def GetTPTSessionInfo(line):
	with open("passwords.txt") as f:
		return f.readlines()[line].strip()

def GetUserID(username):
	page = GetPage("http://powdertoy.co.uk/User.json?Name={}".format(username))
	if not page:
		return -1
	thing = page.find("\"ID\":")
	return page[thing+5:page.find(",", thing)]

#Ban / Unban Functions
def BanUser(username, time, timeunits, reason):
	try:
		userID = int(username)
	except:
		userID = int(GetUserID(username))
	if userID < 0 or userID == 1 or userID == 38642:
		return False
	data = {"BanUser":str(userID).strip("="), "BanReason":reason, "BanTime":time, "BanTimeSpan":timeunits}
	if not GetPage("http://powdertoy.co.uk/User/Moderation.html?ID=%s&Key=%s" % (userID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), data):
		return False
	return True

def UnbanUser(username):
	try:
		userID = int(username)
	except:
		userID = int(GetUserID(username))
	if userID < 0:
		return False
	data = {"UnbanUser":str(userID).strip("=")}
	if not GetPage("http://powdertoy.co.uk/User/Moderation.html?ID=%s&Key=%s" % (userID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), data):
		return True
	return True

#Functions to get info from TPT
def GetPostInfo(postID):
	page = GetPage("http://tpt.io/.%s" % postID)
	match = re.search("<div class=\"Comment\">(.+?<div id=\"MessageContainer-%s\" class=\"Message\">.+?)</li>" % postID, page, re.DOTALL)
	matchinfo = filter(None, re.split("[ \n\t]*<.+?>[ \n\t]*", match.group(1)))
	#"[ \n\t]*</?div.+?>[ \n\t+]*"
	print(matchinfo)

def GetSaveInfo(saveID):
	try:
		page = GetPage("http://powdertoythings.co.uk/Powder/Saves/ViewDetailed.json?ID=%s" % saveID)
		info = json.loads(page)
		return info
	except Exception:
		return None

def FormatDate(unixtime):
	timestruct = time.localtime(unixtime)
	strftime = time.strftime("%a %b %d %Y %I:%M:%S%p", timestruct)
	return strftime

def FormatSaveInfo(info):
	if "Status" in info and info["Status"] == 0:
		return info["Error"]
	elementCount = {}
	for element in info["ElementCount"]:
		elementCount[element["Name"]] = element["Count"]
	elementCountSorted = sorted(elementCount.items(), key=lambda x: x[1], reverse=True)

	mainline = "Save is \x0302%s\x03 (ID:%s) by \x0305%s\x03. Has %s upvotes, %s downvotes, %s views, and %s comments. Created in TPT version %s." % (info["Name"], info["ID"], info["Username"], info["ScoreUp"], info["ScoreDown"], info["Views"], info["Comments"], info["PowderVersion"])
	dateline = "Uploaded on \x0303%s\x03. Updated %s time%s: [%s]" % (FormatDate(info["FirstPublishTime"]), len(info["BumpTimes"]), "" if len(info["BumpTimes"]) == 1 else "s", ", ".join([FormatDate(i) for i in info["BumpTimes"]]))
	descriptionline = "Description: \x0303%s\x03. Tags: [%s]" % (info["Description"], ", ".join(info["Tags"]))
	elementline = "Element Counts: %s" % (", ".join(["\x02%s\x02: %s" % (element[0], element[1]) for element in elementCountSorted]))
	return "%s\n%s\n%s\n%s" % (mainline, dateline, descriptionline, elementline)

#Moderation functions
def HidePost(postID, remove, reason):
	data = {"Hide_Reason":reason,"Hide_Hide":"Hide Post"}
	if remove:
		data["Hide_Remove"] = "1"
	GetPage("http://powdertoy.co.uk/Discussions/Thread/HidePost.html?Post=%s&Key=%s" % (postID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), data)

def UnhidePost(postID):
	GetPage("http://powdertoy.co.uk/Discussions/Thread/UnhidePost.html?Post=%s&Key=%s" % (postID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0))

def LockThread(threadID, reason):
	GetPage("http://powdertoy.co.uk/Discussions/Thread/Moderation.html?Thread=%s" % (threadID), GetTPTSessionInfo(0), {"Moderation_Lock":"Lock Thread", "Moderation_LockReason":reason})

def UnlockThread(threadID):
	GetPage("http://powdertoy.co.uk/Discussions/Thread/Moderation.html?Thread=%s" % (threadID), GetTPTSessionInfo(0), {"Moderation_Unlock":"Unlock"})

def PromotionLevel(saveID, level):
	if level >= -2 and level <= 2:
		if not GetPage("http://powdertoy.co.uk/Browse/View.html?ID=%s&Key=%s" % (saveID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), {"PromoState":str(level)}):
			return False
		return True
	return False

def SaveReports(ID):
	page = GetPage("http://powdertoy.co.uk/Reports/View.html?ID=%s" % ID, GetTPTSessionInfo(0))
	reports = re.findall('<div class="Message">([^<]+)<div class="Clear">', page)
	usernames = re.findall('<a href="/User.html\?ID=[0-9]+">([^<]+)</a>', page)[1:] #ignore "My Profile"
	return list(zip(usernames, reports))

def ReportsList():
	page = GetPage("http://powdertoy.co.uk/Reports.html", GetTPTSessionInfo(0))
	if page:
		matches = re.findall('ReportsCount">([0-9]+)</span>\t\t<span class="SaveName">\t\t\t<a href="/Reports/View.html\?ID=([0-9]+)" target="_blank">\t\t\t\t([^\t]+)\t\t\t</a>\t\t</span> by\t\t<span class="SaveAuthor">([^<]+)<', page)
	else:
		return None
	for match in matches:
		match = (int(match[0]), match[1], match[2])
	return matches

#Prints reports on a save (reporter and report text)
def PrintReports(channel, reportlist):
	h = html.parser.HTMLParser()
	for report in reportlist:
		reporter = report[0]
		text = h.unescape(report[1])
		def replace(match):
			return " http://tpt.io/~" + match.group(1)
		text = re.sub(" ?(?:(?:~|ID:?|id:?|save | )([0-9]{4,}))", replace, text)
		SendMessage(channel, "\00314%s\003: %s" % (reporter, text.strip()))
	if not reportlist:
		SendMessage(channel, "No reports on that save")

#prints the report list (save title, save author, save ID link, report count)
def PrintReportList(channel, reportlist):
	h = html.parser.HTMLParser()
	for report in reportlist:
		ID = report[1]
		count = int(report[0])
		title = h.unescape(report[2])
		author = report[3]
		SendMessage(channel, "\00302%s\003 by \00305%s\003:\00314 http://tpt.io/~%s#Reports, %s report%s" % (title, author, ID, count, "" if count == 1 else "s"))
		reportlist = SaveReports(ID)
		PrintReports(channel, reportlist[:count])

def GetConvoList():
	page = GetPage("http://powdertoy.co.uk/Conversations.html", GetTPTSessionInfo(0))
	if not page:
		return []
	match = re.search(".*conversationsUnread = (.+);</script>.*", page)
	if not match:
		return []
	parsed = json.loads(match.group(1))
	return parsed

def GetLinkedAccounts(account):
	if account.find(".") >= 0:
		page = GetPage("http://powdertoy.co.uk/IPTools/GetInfo.json?IP=%s" % account, GetTPTSessionInfo(0))
	else:
		page = GetPage("http://powdertoy.co.uk/IPTools/GetInfo.json?Username=%s" % account, GetTPTSessionInfo(0))
	if not page:
		return "There was an error fetching the page (probably a timeout)"

	data = json.loads(page)
	if data == False:
		return "Invalid data"

	output = []
	if "Username" in data:
		if "Banned" in data and data["Banned"] == "1":
			output.append("\x02\x0304%s\x02\x03:" % data["Username"])
		else:
			output.append("\x02%s\x02:" % data["Username"])
	elif "Address" in data:
		if "Network" in data and "NetworkTop" in data:
			output.append("\x02%s\x02 (%s - %s):" % (data["Address"], data["Network"], data["NetworkTop"]))
		else:
			output.append("\x02%s\x02:" % data["Address"])
	if "Country" in data:
		if "CountryCode" in data:
			output.append("%s (%s)," % (data["Country"], data["CountryCode"]))
		else:
			output.append("%s," % (data["Country"]))
	if "ISP" in data:
		output.append("%s," % data["ISP"])

	if "Users" in data and len(data["Users"]):
		output.append("Linked Accounts:")
		for userID in data["Users"]:
			if data["Users"][userID]["Banned"] == "1":
				output.append("\x02\x0304%s\x02\x03 (%s)" % (data["Users"][userID]["Username"], userID))
			else:
				output.append("\x02%s\x02 (%s)" % (data["Users"][userID]["Username"], userID,))
	elif "Addresses" in data and len(data["Addresses"]):
		output.append("Linked IPs:")
		output.append(", ".join("%s (%s)" % (ip[0], ip[1]) for ip in data["Addresses"]))
	return " ".join(output)

def DoComment(saveID, message, jacob1 = False):
	if not GetPage("http://powdertoy.co.uk/Browse/View.html?ID=%s" % (saveID), GetTPTSessionInfo(0) if jacob1 else GetTPTSessionInfo(3), {"Comment":message}):
		return False
	return True

def DoUnpublish(saveID):
	if not GetPage("http://powdertoy.co.uk/Browse/View.html?ID=%s&Key=%s" % (saveID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), {"ActionUnpublish":"&nbsp;"}):
		return False
	return True

def DoPublish(saveID):
	if not GetPage("http://powdertoy.co.uk/Browse/View.html?ID=%s&Key=%s" % (saveID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), {"ActionPublish":"&nbsp;"}):
		return False
	return True

@command("ban", minArgs = 4, owner = True)
def Ban(username, hostmask, channel, text, account):
	"""(ban <user ID> <ban time> <ban time units> <reason>). bans someone in TPT. Owner only. Add = to ban usernames that look like IDs"""
	if username != "jacob1":
		SendNotice(username, "Error, only jacob1 should be able to use this command")
	if not BanUser(text[0], text[1], text[2], " ".join(text[3:])):
		SendMessage(channel, "An error occured while trying to ban user.")

@command("unban", minArgs = 1, owner = True)
def Unban(username, hostmask, channel, text, account):
	"""(unban <user ID>). unbans someone in TPT. Owner only."""
	if username != "jacob1":
		SendNotice(username, "Error, only jacob1 should be able to use this command")
	if not UnbanUser(text[0]):
		SendMessage(channel, "An error occured while trying to unban user.")

@command("post", minArgs = 1, admin = True)
def Post(username, hostmask, channel, text, account):
	"""(post <post ID>). Gets info on a TPT post. Admin only."""
	GetPostInfo(text[0])
	
@command("hide", minArgs = 1, owner = True)
def Hide(username, hostmask, channel, text, account):
	"""(hide <post ID> [<reason>]). Hides a post in TPT. Owner only."""
	HidePost(text[0], False, " ".join(text[1:]))

@command("remove", minArgs = 1, admin = True)
def Remove(username, hostmask, channel, text, account):
	"""(remove <post ID> [<reason>]). Removes a post in TPT. Admin only."""
	HidePost(text[0], True, " ".join(text[1:]))

@command("unhide", minArgs = 1, admin = True)
def Unhide(username, hostmask, channel, text, account):
	"""(unhide <post ID>). Unhides a post in TPT. Admin only."""
	UnhidePost(text[0])

@command("lock", minArgs = 2, owner = True)
def Lock(username, hostmask, channel, text, account):
	"""(lock <thread ID> <reason>). Locks a thread in TPT. Owner only."""
	LockThread(text[0], " ".join(text[1:]))

@command("unlock", minArgs = 1, owner = True)
def Unlock(username, hostmask, channel, text, account):
	"""(unlock <thread ID>). Unlocks a thread in TPT. Owner only."""
	UnlockThread(text[0])

@command("promolevel", minArgs = 2, admin = True)
def Unlock(username, hostmask, channel, text, account):
	"""(promolevel <save ID> <level>). Sets the promotion level on a save. Admin only."""
	if PromotionLevel(text[0], int(text[1])):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Invalid promotion level.")

@command("ipmap", minArgs = 1, admin = True)
def IpMap(username, hostmask, channel, text, account):
	"""(ipmap <username/ip>). Prints out linked accounts or IP addresses. Admin only."""
	SendMessage(channel, GetLinkedAccounts(text[0]))

@command("saveinfo", minArgs = 1, admin = True)
def SaveInfo(username, hostmask, channel, text, account):
	"""(saveinfo <saveid>). Prints out lots of useful information about TPT saves. Admin only."""
	info = GetSaveInfo(text[0])
	if info:
		formatted = FormatSaveInfo(info)
		for line in formatted.split("\n"):
			SendMessage(channel, line)
	else:
		SendMessage(channel, "Save info not found")

@command("getreports", minArgs=1, admin = True)
def GetReports(username, hostmask, channel, text, account):
	"""(getreports <saveid> [numreports]). Prints out all (or numreports) reports from a save. Admin only."""
	count = None
	reportlist = SaveReports(text[0])
	if len(text) > 1:
		count = int(text[1])
	PrintReports(channel, reportlist[:count])

@command("markread", minArgs=1, admin = True)
def MarkRead(username, hostmask, channel, text, account):
	"""(markread <saveid>). Marks a report on a save as read. Admin only."""
	GetPage("http://powdertoy.co.uk/Reports.html?Read=%s" % text[0], GetTPTSessionInfo(0))

@command("markallread", admin = True)
def MarkAllRead(username, hostmask, channel, text, account):
	"""(markallread). Marks all reports that have been printed to channel previously as read. Admin only."""
	global seenReports
	reportlist = ReportsList()
	if reportlist == None:
		SendMessage(channel, "Error fetching reports")
		return
	markedread = []
	unread = []
	for report in reportlist:
		if report[1] in seenReports:
			GetPage("http://powdertoy.co.uk/Reports.html?Read=%s" % report[1], GetTPTSessionInfo(0))
			markedread.append(report[1])
		else:
			unread.append(report[1])
	if markedread:
		SendMessage(channel, "These saves were marked as read: %s" % (" ".join(markedread)))
	if unread:
		SendMessage(channel, "These saves still have unread reports: %s" % (" ".join(unread)))

@command("reports", admin = True)
def Reports(username, hostmask, channel, text, account):
	"""(reports) No args. Prints out the reports list. Owner only."""
	global seenReports
	reportlist = ReportsList()
	if reportlist == None:
		SendMessage(channel, "Error fetching reports")
		return
	elif len(reportlist) == 0:
		SendMessage(channel, "No reports")
	else:
		PrintReportList(channel, reportlist)

	seenReports = {}
	for report in reportlist:
		seenReports[report[1]] = report[0]

@command("comment", minArgs=2, owner = True)
def Comment(username, hostmask, channel, text, account):
	"""(comment <saveID> <comment>). Comments on a save as jacobot. Admin only."""
	if DoComment(text[0], " ".join(text[1:]), False):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error, could not comment.")

@command("commentj1", minArgs=2, owner = True)
def Comment(username, hostmask, channel, text, account):
	"""(commentj1 <saveID> <comment>). Comments on a save as jacob1. Owner only."""
	if DoComment(text[0], " ".join(text[1:]), True):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error, could not comment.")

@command("unpublish", minArgs=1, admin = True)
def Unpublish(username, hostmask, channel, text, account):
	"""(unpublish <saveID>). Unpublishes a save. Admin only."""
	DoUnpublish(text[0])
	SendMessage(channel, "Done.")

@command("publish", minArgs=1, admin = True)
def Publish(username, hostmask, channel, text, account):
	"""(publish <saveID>). Publishes a save. Admin only."""
	DoPublish(text[0])
	SendMessage(channel, "Done.")

@command("readreport", minArgs=2, admin = True)
def Stolen(username, hostmask, channel, text, account):
	"""(readreport <saveID> <comment>). Disables a save and comments with a message as jacobot. Admin only."""
	saveID = text[0]
	#DoUnpublish(saveID)
	ret = PromotionLevel(saveID, -2)
	if ret:
		print("test", " ".join(text[1:]))
		ret = DoComment(saveID, " ".join(text[1:]))
		if ret:
			SendMessage(channel, "Done.")
		else:
			SendMessage(channel, "Error, could not comment.")
	else:
		SendMessage(channel, "Error, could not disable save.")

@command("copied", minArgs=2, admin = True)
def Copied(username, hostmask, channel, text, account):
	"""(copied <copiedID> <originalID> [long/<reason>]). Unpublishes a save and leaves a comment by jacobot with the original saveID, save name, and author. Optional message can be appended to the end. Admin only."""
	stolenID = text[0]
	saveID = text[1]
	try:
		if int(stolenID) <= int(saveID):
			SendMessage(channel, "Error: stolenID can't be less than originalID.")
			return
	except ValueError:
		SendMessage(channel, "Error: saveIDs must be integers")
		return
	if not DoUnpublish(stolenID):
		SendMessage(channel, "Error unpublishing save.")
		return
	info = GetSaveInfo(saveID)
	if info:
		message = "Save unpublished: copied without credit from id:%s (save \"%s\" by %s)." % (saveID, info["Name"], info["Username"])
		if len(text) > 2 and text[2] != "long":
			message = "%s %s" % (message, " ".join(text[2:]))
		else:
			message = message +" Please give credit to the original owner when modifying saves."
			if len(text) > 2 and text[2] == "long":
				message = message + "Alternatively, you can \"Favorite\" the save or save it locally to your computer."
		if DoComment(stolenID, message):
			SendMessage(channel, "Done.")
		else:
			SendMessage(channel, "Error commenting.")
	else:
		SendMessage(channel, "Error getting original save info.")

@command("stolen", minArgs=2, admin = True)
def Stolen(username, hostmask, channel, text, account):
	"""(stolen <stolenID> <originalID> [long/<reason>]). Disables a save and leaves a comment by jacobot with the original saveID, save name, and author. Optional message can be appended to the end, or 'long' for default optional message. Admin only."""
	stolenID = text[0]
	saveID = text[1]
	try:
		if int(stolenID) <= int(saveID):
			SendMessage(channel, "Error: stolenID can't be less than originalID.")
			return
	except ValueError:
		SendMessage(channel, "Error: saveIDs must be integers")
		return
	if not PromotionLevel(stolenID, -2):
		SendMessage(channel, "Error unpublishing save.")
		return
	info = GetSaveInfo(saveID)
	if info:
		message = "Save unpublished: stolen from id:%s (save \"%s\" by %s)." % (saveID, info["Name"], info["Username"])
		if len(text) > 2:
			if text[2] == "long":
				message += " Do not publish copies of other player's saves, instead you should \"Favorite\" the save or save it locally to your computer."
			else:
				message += " " + " ".join(text[2:])
		if DoComment(stolenID, message):
			SendMessage(channel, "Done.")
		else:
			SendMessage(channel, "Error commenting.")
	else:
		SendMessage(channel, "Error getting original save info.")

@command("updatetor", admin = True)
def UpdateTor(username, hostmask, channel, text, account):
	"""(no args). Update the list of TOR ip addresses. Admin only."""
	torlist = GetPage("https://www.dan.me.uk/torlist/")
	if not torlist:
		SendMessage(channel, "Error fetching tor list")
		return
	torfile = open("torlist.txt", "w")
	torfile.write(torlist)
	torfile.close()
	SendMessage(channel, "Updated list of TOR IPs, there are now %s IPs" % (len(torlist.splitlines())))

@command("ipban", minArgs = 1, admin = True)
def IPban(username, hostmask, channel, text, account):
	"""(ipban add <ip>|remove <ip>|list). Modifies the IP bans list. Owner only."""
	if text[0].lower() == "list":
		if not ipbans:
			SendMessage(channel, "Nobody is currently IP banned")
		else:
			SendMessage(channel, "List of currently banned IPs: " + ", ".join(ipbans))
	elif len(text) > 1:
		action = text[0].lower()
		if action == "remove":
			ipbans.discard(text[1])
			SendMessage(channel, "Removed %s from the IP ban list" % text[1])
		elif action == "add":
			ipbans.add(text[1])
			SendMessage(channel, "Added %s to the IP ban list" % text[1])
		else:
			SendMessage(channel, "Unknown action")
	else:
		SendMessage(channel, "Unknown action")
