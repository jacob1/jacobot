import html.parser
import json
import time
import re
import ast
from datetime import datetime
from time import sleep
from collections import defaultdict

from common import *
RegisterMod(__name__)

# Load banned ips / tags from file
try:
	bannedfile = open("mods/BANNED.txt")
	bannedstuff = bannedfile.readlines()
	bannedfile.close()
	ipbans = ast.literal_eval(bannedstuff[0])
	bannedtags = ast.literal_eval(bannedstuff[1])
except IOError:
	ipbans = {}
	bannedtags = {}
	pass

def CheckIP(IP):
	torfile = open("torlist.txt")
	torips = torfile.readlines()
	torfile.close()
	torips = map(lambda ip: ip.strip(), torips)
	if IP in torips:
		return (True, "tor")
	for address in ipbans:
		if IP.startswith(address):
			return (True, "ipban")
	return (False, "")

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
			BanUser(match.group(1), "1", "p", "Automatic ban: Registeration using TOR has been temporarily disabled due to abuse")
	#match = re.match("^:(?:StewieGriffinSub|PowderBot)!(?:Stewie|jacksonmj3|bagels)@turing.jacksonmj.co.uk PRIVMSG #powder-saves :Warning: LCRY, Percentage: ([0-9.]+), https?:\/\/tpt.io\/~([0-9]+)$", raw)
													#New: 'Deut compressor' by HugInfinity (0 comments, score 1, 1 bump); http://tpt.io/~1973995
	"""match = re.match("^:(?:StewieGriffinSub|PowderBot)!(?:Stewie|jacksonmj3|bagels)@turing.jacksonmj.co.uk PRIVMSG #powder-saves :New: \u000302'(.+?)'\u000F by\u000305 ([\w_-]+)\u000314 \(.*?\)\u000F; https?:\/\/tpt.io\/~([0-9]+)$", raw)
	if match:
		saveID = match.group(3)
		name = match.group(1)
		if "cow" in name.lower():
			if not PromotionLevel(saveID, -1):
				SendMessage("+#powder-saves", "Error demoting save ID %s" % (saveID))
			else:
				SendMessage("+#powder-saves", "Demoted save ID %s" % (saveID))
		info = GetSaveInfoDetailed(saveID)
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
	# Nicer formated PowderBot parser, that doesn't duplicate the long regex (TODO: move stuff to this)
	powderBotMatch = re.match("^:(?:StewieGriffinSub|PowderBot)!(?:Stewie|jacksonmj3|bagels)@turing.jacksonmj.co.uk PRIVMSG (#{1,}[\w-]+) :(.*)$", raw)
	if powderBotMatch:
		channel = powderBotMatch.group(1)
		message = powderBotMatch.group(2)
		if channel == "#powder-saves":
			CheckTag(message)
		elif channel == "#powder-forum":
			CheckPost(message)
		#elif channel == "#powder-info":
		#	CheckPost(message)

def CheckTag(message):
	tagMatch = re.match("^New tag: \u000303(\w+)\u0003 \(http://tpt.io/~(\d+)\)$", message)
	if tagMatch:
		tag = tagMatch.group(1)
		saveID = tagMatch.group(2)
		for banned in bannedtags:
			if re.fullmatch(banned, tag):
				username = GetTagUsage(tag, saveID)
				if DisableTag(tag):
					SendMessage("+#powder-saves", "Disabled tag {0} by {1}".format(tag, username if username else "UNKNOWN"))
				else:
					SendMessage("+#powder-saves", "Error: couldn't disable tag {0}".format(tag))

def CheckPost(message):
	logchan = "+#powder-forum"
	postMatch = re.match("^Post by \u000305(\w+)\u000F in '\u000302([^\u000F]+)\u000F'; http://tpt.io/.(\d+)$", message)
	if postMatch:
		#SendMessage("#powder-info", "Match: {0}, {1}, {2}".format(postMatch.group(1), postMatch.group(2), postMatch.group(3)))
		postID = postMatch.group(3)
		IP = GetPostIP(postID)
		username = postMatch.group(1)
		check = CheckIP(IP)
		if check[0] and check[1] == "tor":
			if HidePost(postID, True, "This post has been automatically removed due to potential abuse."):
				SendMessage(logchan, "Warning: This post was made using TOR. Removed post.")
			else:
				SendMessage(logchan, "Warning: This post was made using TOR. Error removing post, please remove manually.")
		elif check[0] and check[1] == "ipban":
			if HidePost(postID, True, "This post has been automatically removed due to potential abuse."):
				SendMessage(logchan, "Warning: This post was made from a suspicious IP address. Removed post.")
			else:
				SendMessage(logchan, "Warning: This post was made from a suspicious IP address. Error removing post, please remove manually.")
	threadMatch = re.match("^Thread '\u000302([^']+)\u000F' by \u000305(\w+)\u000F in (?:.*?); http://tpt.io/:(\d+)$", message)
	if threadMatch:
		#SendMessage("#powder-info", "Thread Match: {0}, {1}, {2}".format(threadMatch.group(1), threadMatch.group(2), threadMatch.group(3)))
		threadID = threadMatch.group(3)
		IP = GetThreadPostIP(threadMatch.group(3))
		check = CheckIP(IP)
		if check[0] and check[1] == "tor":
			SendMessage(logchan, "Warning: This thread was made using TOR. Removing thread.")
			MoveThread(threadID, 7)
			LockThread(threadID, "Thread automatically moved and locked because it was posted with TOR")
		elif check[0]:
			SendMessage(logchan, "Warning: This thread was made from a suspicious IP address.")

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
	if now.hour == 6 and now.minute == 1 and now.second == 4:
		torlist = GetPage("https://www.dan.me.uk/torlist/")
		if not torlist:
			SendMessage("#powder-info", "Error fetching tor list")
			return
		torfile = open("torlist.txt", "w")
		torfile.write(torlist)
		torfile.close()
		SendMessage("#powder-info", "Updated list of TOR IPs, there are now %s IPs" % (len(torlist.splitlines())))

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
def GetSaveInfoDetailed(saveID):
	try:
		page = GetPage("http://powdertoythings.co.uk/Powder/Saves/ViewDetailed.json?ID=%s" % saveID)
		info = json.loads(page)
		return info
	except Exception:
		return None

def GetSaveInfo(saveID):
	try:
		page = GetPage("http://powdertoy.co.uk/Browse/View.json?ID=%s" % saveID)
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
	page = GetPage("http://powdertoy.co.uk/Discussions/Thread/HidePost.html?Post=%s&Key=%s" % (postID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), data)
	if page and page.find("The post you are trying to edit could not be found.") == -1:
		return True
	return False

def UnhidePost(postID):
	return GetPage("http://powdertoy.co.uk/Discussions/Thread/UnhidePost.html?Post=%s&Key=%s" % (postID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0))

def LockThread(threadID, reason):
	GetPage("http://powdertoy.co.uk/Discussions/Thread/Moderation.html?Thread=%s" % (threadID), GetTPTSessionInfo(0), {"Moderation_Lock":"Lock Thread", "Moderation_LockReason":reason})

def UnlockThread(threadID):
	GetPage("http://powdertoy.co.uk/Discussions/Thread/Moderation.html?Thread=%s" % (threadID), GetTPTSessionInfo(0), {"Moderation_Unlock":"Unlock"})

def MoveThread(threadID, newSection):
	GetPage("http://powdertoy.co.uk/Discussions/Thread/Moderation.html?Thread=%s" % (threadID), GetTPTSessionInfo(0), {"Moderation_Move":"Move Thread", "Moderation_MoveCategory":newSection})

def PromotionLevel(saveID, level):
	if level >= -2 and level <= 2:
		if not GetPage("http://powdertoy.co.uk/Browse/View.html?ID=%s&Key=%s" % (saveID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), {"PromoState":str(level)}):
			return False
		return True
	return False

def SaveReports(ID):
	page = GetPage("http://powdertoy.co.uk/Reports/View.html?ID=%s" % ID, GetTPTSessionInfo(0))
	reports = re.findall('<div class="Message">([^<]+)<div class="Clear">', page)
	usernames = re.findall('<a href="/User.html\?Name=[a-zA-Z0-9_-]+">([^<]+)</a>', page)[1:] #ignore "My Profile"
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
def PrintReports(channel, reportlist, saveID=None):
	h = html.parser.HTMLParser()
	showtags = False
	for report in reportlist:
		reporter = report[0]
		text = h.unescape(report[1])
		def replace(match):
			return " http://tpt.io/~" + match.group(1)
		text = re.sub(" ?(?:(?:~|ID:?|id:?|save | |^)([0-9]{4,}))", replace, text)
		SendMessage(channel, "\00314%s\003: %s" % (reporter, text.strip()))
		if re.search("(?:tags| tag(?:$| |\.))", text.lower()):
			showtags = True
	if not reportlist:
		SendMessage(channel, "No reports on that save")
	if showtags and saveID:
		PrintTags(channel, saveID)

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
		PrintReports(channel, reportlist[:count], ID)

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

def PrintTags(channel, saveID):
	saveInfo = GetSaveInfo(saveID)
	if not saveInfo:
		SendMessage(channel, "Error: Could not load save info")
	elif "Tags" in saveInfo and saveInfo["Tags"]:
		SendMessage(channel, "Tags: {0}".format(", ".join(saveInfo["Tags"])))
	else:
		SendMessage(channel, "No tags on that save")

def GetTagUsage(tag, saveID):
	usages = GetPage("http://powdertoy.co.uk/Browse/Tag.xhtml?Tag={0}&SaveID={1}".format(tag, saveID), GetTPTSessionInfo(0))
	username = re.search("<a href=\"\/User\.html\?Name=([\w_]+)\">[\w_]+<\/a>", usages)
	return username.group(1) if username else None

def GetTagUsages(tag):
	usages = GetPage("http://powdertoy.co.uk/Browse/Tag.xhtml?Tag={0}".format(tag), GetTPTSessionInfo(0))
	tags = re.findall("<a href=\"\/Browse\/View.html\?ID=(\d+)\">\d+<\/a> by <a href=\"\/User.html\?Name=([\w-]+)\">[\w-]+<\/a>", usages)
	return {"count":len(tags), "usages":tags}

def RemoveTag(tag, saveID):
	if GetPage("http://powdertoy.co.uk/Browse/EditTag.json?Op=delete&ID={0}&Tag={1}&Key={2}".format(saveID, tag, GetTPTSessionInfo(1)), GetTPTSessionInfo(0)):
		return True
	return False

def DisableTag(tag, undelete=False):
	if GetPage("http://powdertoy.co.uk/Browse/Tags.json?{0}={1}&Key={2}".format("UnDelete" if undelete else "Delete", tag, GetTPTSessionInfo(1)), GetTPTSessionInfo(0)):
		return True
	return False

def GetUserComments(username, page=0):
	try:
		userID = int(username)
	except:
		userID = int(GetUserID(username))
	page = GetPage("http://powdertoy.co.uk/User/Moderation.html?ID={0}&PageNum={1}".format(userID, page), GetTPTSessionInfo(0))
	comments = re.findall("\?ID=(\d+)&DeleteComment=(\d+)&.*\n.*\n.*Message\">(.*?)<", page)
	return comments

def GetSaveComments(saveID, page=0):
	page = GetPage("http://powdertoy.co.uk/Browse/View.html?ID={0}&PageNum={1}".format(saveID, page), GetTPTSessionInfo(0))
	comments = re.findall("\/User\.html\?Name=([\w_-]+)\">.*\n.*\n.*\n.*\/Browse\/View\.html\?ID=(\d+)&amp;DeleteComment=(\d+)\".*\n.*\n.*Message\">(.*?)<", page)
	return comments

def DeleteComment(saveID, commentID, safe=True):
	saveComments = GetSaveComments(saveID)
	try:
		if saveComments[0][2] != commentID:
			return True
	# Save doesn't exist
	except IndexError:
		return True
	if GetPage("http://powdertoy.co.uk/Browse/View.html?ID={0}&DeleteComment={1}".format(saveID, commentID), GetTPTSessionInfo(0)):
		return True
	return False

def GetPostIP(postID):
	redirect = GetPage("http://powdertoy.co.uk/Discussions/Thread/View.html?Post={0}".format(postID), getredirect=True)
	if redirect:
		page = GetPage(redirect, GetTPTSessionInfo(0))
		IP = re.search("\/IPTools\.html[^>]+>(\d{{1,3}}\.\d{{1,3}}\.\d{{1,3}}\.\d{{1,3}})<\/a>\s+<a[^>]+EditPost.html\?Post={0}\"".format(postID), page)
		if IP:
			return IP.group(1)
	return None

def GetThreadPostIP(threadID):
	page = GetPage("http://powdertoy.co.uk/Discussions/Thread/View.html?Thread={0}".format(threadID), GetTPTSessionInfo(0))
	if page:
		IP = re.search("\/IPTools\.html[^>]+>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})<\/a>", page)
		if IP:
			return IP.group(1)
	return None

@command("ban", minArgs = 4, owner = True)
def Ban(username, hostmask, channel, text):
	"""(ban <user ID> <ban time> <ban time units> <reason>). bans someone in TPT. Owner only. Add = to ban usernames that look like IDs"""
	if username != "jacob1":
		SendNotice(username, "Error, only jacob1 should be able to use this command")
	if not BanUser(text[0], text[1], text[2], " ".join(text[3:])):
		SendMessage(channel, "An error occured while trying to ban user.")

@command("unban", minArgs = 1, owner = True)
def Unban(username, hostmask, channel, text):
	"""(unban <user ID>). unbans someone in TPT. Owner only."""
	if username != "jacob1":
		SendNotice(username, "Error, only jacob1 should be able to use this command")
	if not UnbanUser(text[0]):
		SendMessage(channel, "An error occured while trying to unban user.")

@command("hide", minArgs = 1, owner = True)
def Hide(username, hostmask, channel, text):
	"""(hide <post ID> [<reason>]). Hides a post in TPT. Owner only."""
	if HidePost(text[0], False, " ".join(text[1:])):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error hiding post.")

@command("remove", minArgs = 1, admin = True)
def Remove(username, hostmask, channel, text):
	"""(remove <post ID> [<reason>]). Removes a post in TPT. Admin only."""
	if HidePost(text[0], True, " ".join(text[1:])):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error hiding post.")

@command("unhide", minArgs = 1, admin = True)
def Unhide(username, hostmask, channel, text):
	"""(unhide <post ID>). Unhides a post in TPT. Admin only."""
	if UnhidePost(text[0]):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error hiding post.")

@command("lock", minArgs = 2, owner = True)
def Lock(username, hostmask, channel, text):
	"""(lock <thread ID> <reason>). Locks a thread in TPT. Owner only."""
	LockThread(text[0], " ".join(text[1:]))
	SendMessage(channel, "No output.")

@command("unlock", minArgs = 1, owner = True)
def Unlock(username, hostmask, channel, text):
	"""(unlock <thread ID>). Unlocks a thread in TPT. Owner only."""
	UnlockThread(text[0])
	SendMessage(channel, "No output.")

@command("move", minArgs = 2, admin = True)
def Unlock(username, hostmask, channel, text):
	"""(move <thread ID> <new section>). Moves a thread into a new section. Must use forum section IDs, not names. Admin only."""
	MoveThread(text[0], text[1])
	SendMessage(channel, "No output.")

@command("promolevel", minArgs = 2, admin = True)
def Unlock(username, hostmask, channel, text):
	"""(promolevel <save ID> <level>). Sets the promotion level on a save. Admin only."""
	if PromotionLevel(text[0], int(text[1])):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Invalid promotion level.")

@command("ipmap", minArgs = 1, admin = True)
def IpMap(username, hostmask, channel, text):
	"""(ipmap <username/ip>). Prints out linked accounts or IP addresses. Admin only."""
	SendMessage(channel, GetLinkedAccounts(text[0]))

@command("saveinfo", minArgs = 1, admin = True)
def SaveInfo(username, hostmask, channel, text):
	"""(saveinfo <saveid>). Prints out lots of useful information about TPT saves. Admin only."""
	info = GetSaveInfoDetailed(text[0])
	if info:
		formatted = FormatSaveInfo(info)
		for line in formatted.split("\n"):
			SendMessage(channel, line)
	else:
		SendMessage(channel, "Save info not found")

@command("getreports", minArgs=1, admin = True)
def GetReports(username, hostmask, channel, text):
	"""(getreports <saveid> [numreports]). Prints out all (or numreports) reports from a save. Admin only."""
	count = None
	reportlist = SaveReports(text[0])
	if len(text) > 1:
		count = int(text[1])
	PrintReports(channel, reportlist[:count])

@command("markread", minArgs=1, admin = True)
def MarkRead(username, hostmask, channel, text):
	"""(markread <saveid>). Marks a report on a save as read. Admin only."""
	GetPage("http://powdertoy.co.uk/Reports.html?Read=%s" % text[0], GetTPTSessionInfo(0))

@command("markallread", admin = True)
def MarkAllRead(username, hostmask, channel, text):
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
def Reports(username, hostmask, channel, text):
	"""(reports) No args. Prints out the reports list. Admin only."""
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

@command("comment", minArgs=2, admin = True)
def Comment(username, hostmask, channel, text):
	"""(comment <saveID> <comment>). Comments on a save as jacobot. Admin only."""
	if DoComment(text[0], " ".join(text[1:]), False):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error, could not comment.")

@command("commentj1", minArgs=2, owner = True)
def Comment(username, hostmask, channel, text):
	"""(commentj1 <saveID> <comment>). Comments on a save as jacob1. Owner only."""
	if DoComment(text[0], " ".join(text[1:]), True):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error, could not comment.")

@command("unpublish", minArgs=1, admin = True)
def Unpublish(username, hostmask, channel, text):
	"""(unpublish <saveID>). Unpublishes a save. Admin only."""
	DoUnpublish(text[0])
	SendMessage(channel, "Done.")

@command("publish", minArgs=1, admin = True)
def Publish(username, hostmask, channel, text):
	"""(publish <saveID>). Publishes a save. Admin only."""
	DoPublish(text[0])
	SendMessage(channel, "Done.")

@command("listtags", minArgs=1, admin=True)
def ListTags(username, hostmask, channel, text):
	"""(listtags <saveID>). Lists tags on a save. Admin only."""
	PrintTags(channel, text[0])

@command("showtag", minArgs=1, admin=True)
def ShowTag(username, hostmask, channel, text):
	"""(showtag <tag>). Shows where tags have been used. Admin only."""
	data = GetTagUsages(text[0])
	if data["count"] > 40:
		usercounts = defaultdict(int)
		for tag in data["usages"]:
			usercounts[tag[1]] = usercounts[tag[1]] + 1
		top = sorted(usercounts.items(), key=lambda a: a[1])[:-30:-1]
		SendMessage(channel, "Tag used {0} times, by: {1}".format(data["count"], ", ".join(["{0} x{1}".format(usertag[0], usertag[1]) for usertag in top])))
	else:
		prepend = "http://tpt.io/:" if data["count"] < 20 else ""
		msg = []
		for tag in data["usages"]:
			msg.append("{0}{1} : {2}".format(prepend, tag[0], tag[1]))
		SendMessage(channel, "Tag used {0} times. {1}".format(data["count"], ", ".join(msg)))

@command("removetag", minArgs=2, admin=True)
def RemoveTagCmd(username, hostmask, channel, text):
	"""(removetag <tag> <saveID>). Removes a tag on a save. Admin only."""
	if RemoveTag(text[0], text[1]):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error, could not remove tag.")

@command("disabletag", minArgs=1, admin=True)
def DisableTagCmd(username, hostmask, channel, text):
	"""(disabletag <tag>). Disables a tag. Admin only."""
	if len(text) > 1:
		fail = False
		for tag in text:
			if not DisableTag(tag):
				fail = True
				break
	else:
		fail = DisableTag(text[0])
	if not fail:
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error, could not disable tag{0}.".format("" if len(text) == 1 else "s"))

@command("enabletag", minArgs=1, admin=True)
def DisableTagCmd(username, hostmask, channel, text):
	"""(enabetag <tag>). Enables a tag. Admin only."""
	if DisableTag(text[0], True):
		SendMessage(channel, "Done.")
	else:
		SendMessage(channel, "Error, could not disable tag.")

@command("bannedtags", minArgs = 1, admin = True)
def IPban(username, hostmask, channel, text):
	"""(bannedtags add <tagregex>|remove <tagregex>|list). Modifies the banned tag regex list. Admin only."""
	if text[0].lower() == "list":
		if not bannedtags:
			SendMessage(channel, "No banned tag regexes")
		else:
			SendMessage(channel, "Banned tag regexes: " + ", ".join(bannedtags))
		return
	action = text[0].lower()
	if action == "remove":
		bannedtags.discard(text[1])
		SendMessage(channel, "Removed %s from the banned tag regex list" % text[1])
	elif action == "add":
		bannedtags.add(text[1])
		SendMessage(channel, "Added %s to the banned tag regex list" % text[1])
	else:
		SendMessage(channel, "Unknown action")

@command("readreport", minArgs=2, admin = True)
def Stolen(username, hostmask, channel, text):
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
def Copied(username, hostmask, channel, text):
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
def Stolen(username, hostmask, channel, text):
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
def UpdateTor(username, hostmask, channel, text):
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
def IPban(username, hostmask, channel, text):
	"""(ipban add <ip>|remove <ip>|list). Modifies the IP bans list. Admin only."""
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

@command("getusercomments", minArgs=1, owner = True)
def GetUserCommentsCmd(username, hostmask, channel, text):
	"""(getusercomments <userID/username> [<pagenumber>]). Debug command to print comments by a certain user. Owner only."""
	SendMessage(channel, str(GetUserComments(text[0], text[1] if len(text) > 1 else 0)))

@command("getsavecomments", minArgs=1, owner = True)
def GetSaveCommentsCmd(username, hostmask, channel, text):
	"""(getsavecomments <saveID> [<pagenum>]). Debug command to print comments on a save. Owner only."""
	SendMessage(channel, str(GetSaveComments(text[0], text[1] if len(text) > 1 else 0)))

@command("deleteusercomments", minArgs=1, admin=True)
def DeleteUserCommentsCmd(username, hostmask, channel, text):
	"""(deleteusercomments <userID/username> [<pagenumber>]). Deletes all comments by a user on a certain page (as long as the comments are the most recent comments on their respective saves). Admin only."""
	pagenum = text[1] if len(text) > 1 else 0
	try:
		if int(pagenum) < 0:
			SendMessage(channel, "Error: pagenum must be a positive integer")
			return
	except ValueError:
		SendMessage(channel, "Error: pagenum must be a positive integer")
		return
	comments = GetUserComments(text[0], text[1] if len(text) > 1 else 0)
	for comment in comments:
		if not DeleteComment(comment[0], comment[1]):
			SendMessage(channel, "Error deleting comment #{0} on ID:{1}".format(comment[1], comment[0]))
			break
	SendMessage(channel, "Done.")

@command("getpostip", minArgs=1, admin=True)
def GetPostIPCmd(username, hostmask, channel, text):
	"""(getpostip <postID>). Returns the IP used to make a forum post. Admin only."""
	postIP = GetPostIP(text[0])
	if postIP:
		suspicious, reason = CheckIP(postIP)
		if suspicious:
			SendMessage(channel, "{0}: this IP is in the {1} blacklist".format(postIP, reason))
		else:
			SendMessage(channel, postIP)
	else:
		SendMessage(channel, "Error: Could not get IP")

@command("getthreadpostip", minArgs=1, admin=True)
def GetThreadPostIPCmd(username, hostmask, channel, text):
	"""(getthreadpostip <postID>). Returns the IP used to make a forum thread. Admin only."""
	threadIP = GetThreadPostIP(text[0])
	if threadIP:
		SendMessage(channel, threadIP)
	else:
		SendMessage(channel, "Error: Could not get IP")
