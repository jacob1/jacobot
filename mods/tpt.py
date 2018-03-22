import html.parser
import json
import time
import re
from datetime import datetime, timedelta
from time import sleep
from collections import defaultdict

from common import *
RegisterMod(__name__)

AddSetting(__name__, "info-chan", "#powder-info")
AddSetting(__name__, "forum-chan", "#powder-forum")
AddSetting(__name__, "saves-chan", "#powder-saves")
AddSetting(__name__, "email-url", "")
LoadSettings(__name__)

emailmap = {}

def CheckUsername(username):
	if username in emailmap:
		provider = emailmap[username].split("@")[1]
		if provider == "126.com":
			return (True, "126.com")
	return False

def CheckIP(IP):
	torfile = open("torlist.txt")
	torips = torfile.readlines()
	torfile.close()
	torips = map(lambda ip: ip.strip(), torips)
	if IP in torips:
		return (True, "tor")
	ipbans = GetData(__name__, "ipbans")
	if ipbans:
		todel = []
		ret = None
		for address, info in ipbans.items():
			expires = info["expires"]
			if expires and time.time() > info["expires"]:
				todel.append(address)
			elif IP.startswith(address):
				ret = (True, "ipban")
		if todel:
			for d in todel:
				del ipbans[d]
				SendMessage(GetSetting(__name__, "info-chan"), "IP ban expired: {0}".format(d))
			StoreData(__name__, "ipbans", ipbans)
		if ret:
			return ret
	if IP.startswith("83.8.") or IP.startswith("83.11.") or IP.startswith("83.25.") or IP.startswith("79.184.") or IP.startswith("79.186."):
		return (True, "neostrada")
	return (False, "")

def CheckForumSpam(ip):
	try:
		page = GetPage("https://api.stopforumspam.org/api?ip={0}&json".format(ip))
		data = json.loads(page)
		return data
	except Exception:
		pass

def Parse(raw, text):
	powderBotMatch = re.match("^:(?:StewieGriffinSub|PowderBot)!(?:Stewie|jacksonmj3|bagels|Shenanigan|jacob1)@turing.jacksonmj.co.uk PRIVMSG (#{1,}[\w-]+) :(.*)$", raw)
	if powderBotMatch:
		channel = powderBotMatch.group(1)
		message = powderBotMatch.group(2)
		if channel == GetSetting(__name__, "saves-chan"):
			CheckTag(message)
		elif channel == GetSetting(__name__, "forum-chan"):
			CheckPost(message)
		elif channel == GetSetting(__name__, "info-chan"):
			CheckRegistration(message)
			#CheckPost(message)

def CheckRegistrationForumSpam(username, IP):
	data = CheckForumSpam(IP)
	if not data:
		SendMessage(GetSetting(__name__, "info-chan"), "Error: Could not access checkforumspam.org")
		return
	if not "ip" in data:
		return
	if not "confidence" in data["ip"]:
		return
	confidence = data["ip"]["confidence"]
	frequency = data["ip"].get("frequency", 0)
	SendMessage(GetSetting(__name__, "info-chan"), "{0}% chance of being a spammer, seen {1} times".format(confidence, frequency))
	if int(confidence) > 10 or int(frequency) > 10:
		#BanUser(username, "1", "p", "Automatic ban: this IP address has been reported as spam")
		return True
	return False

def CheckRegistrationEmail(username, IP):
	email = GetEmail(username)
	if not email:
		return
	provider = email.split("@")[1]
	"""if "shitmail" in provider:
		#SendMessage(GetSetting(__name__, "info-chan"), "bad email test")
		BanUser(username, "1", "p", "Automatic ban: this IP address has been blacklisted")
		expireTime = int(time.time()+timedelta(days=30).total_seconds())
		info = {"reason":"automatically added due to email", "expires":expireTime}
		ipbans = GetData(__name__, "ipbans")
		ipbans[IP] = info
		StoreData(__name__, "ipbans", ipbans)
		SendMessage(GetSetting(__name__, "info-chan"), "Added {0} to the ipban list".format(IP))
		return True"""
	if provider == "126.com":
		SendMessage(GetSetting(__name__, "info-chan"), "Warning: suspicious email: {0}".format(email))
	emailmap[username] = email
	return False

def CheckRegistration(message):
	registrationMatch = re.match(r"^New registration: ([\w_-]+)\. https?:\/\/tpt\.io\/@([\w\_-]+) \[([0-9.]+)\] ?$", message)
	if registrationMatch:
		username = registrationMatch.group(1)
		IP = registrationMatch.group(3)
		check = CheckIP(IP)
		if not check[0]:
			if CheckRegistrationForumSpam(username, IP):
				return
			if CheckRegistrationEmail(username, IP):
				return
			return
		if check[1] == "tor":
			SendMessage(GetSetting(__name__, "info-chan"), "Warning: This account was registered using TOR")
			#BanUser(username, "1", "p", "Automatic ban: Registeration using TOR has been temporarily disabled due to abuse")
		elif check[1] == "ipban":
			BanUser(username, "1", "p", "Automatic ban: this IP address has been blacklisted")
			SendMessage(GetSetting(__name__, "info-chan"), "Automatic ban: this IP address has been blacklisted")
		elif check[1] == "neostrada":
			SendMessage(GetSetting(__name__, "info-chan"), "Warning: this account was registered with Neostrada Plus")
	massRegistrationMatch = re.match(r"^Warning: MassRegistration, (\d) registrations from the same IP in 30 minutes, Username: '([\w_-]+)' http://tpt.io/@(?:[\w_-]+)", message)
	if massRegistrationMatch:
		num = int(massRegistrationMatch.group(1))
		username = massRegistrationMatch.group(2)
		if num > 3:
			#SendMessage(GetSetting(__name__, "info-chan"), "Mass Registration detected from {0}".format(username))
			BanUser(username, "2", "d", "Automatic ban: You are registering accounts too quickly")

def CheckTag(message):
	logchan = "+"+GetSetting(__name__, "saves-chan")
	tagMatch = re.match("^New tag: \u000303(\w+)\u0003 \(http://tpt.io/~(\d+)\)$", message)
	if tagMatch:
		tag = tagMatch.group(1)
		saveID = tagMatch.group(2)
		for banned in GetData(__name__, "bannedtags"):
			if re.fullmatch(banned, tag):
				username = GetTagUsage(tag, saveID)
				if DisableTag(tag):
					SendMessage(logchan, "Disabled tag {0} by {1}".format(tag, username if username else "UNKNOWN"))
				else:
					SendMessage(logchan, "Error: couldn't disable tag {0}".format(tag))

def CheckPost(message):
	logchan = "+"+GetSetting(__name__, "forum-chan")
	postMatch = re.match("^Post by \u000305(\w+)\u000F in '\u000302([^\u000F]+)\u000F'; http://tpt.io/.(\d+)$", message)
	if postMatch:
		#SendMessage(GetSetting(__name__, "info-chan"), "Match: {0}, {1}, {2}".format(postMatch.group(1), postMatch.group(2), postMatch.group(3)))
		postID = postMatch.group(3)
		IP = GetPostIP(postID)
		username = postMatch.group(1)
		if username == "JanKaszanka":
			return
		if IP:
			check = CheckIP(IP)
		else:
			check = (0,0)
			SendMessage(logchan, "Error getting post IP.")
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
		#SendMessage(GetSetting(__name__, "info-chan"), "Thread Match: {0}, {1}, {2}".format(threadMatch.group(1), threadMatch.group(2), threadMatch.group(3)))
		threadTitle = threadMatch.group(1)
		threadID = threadMatch.group(3)
		IP = GetThreadPostIP(threadMatch.group(3))
		username = threadMatch.group(2)

		if "0800" in threadTitle or "number" in threadTitle.lower():
			SendMessage(logchan, "Removing thread due to potential spam.")
			MoveThread(threadID, 7)
			LockThread(threadID, "Thread automatically moved and locked because it was detected as spam")

		if username == "JanKaszanka":
			return
		if IP:
			check = CheckIP(IP)
		else:
			check = (0,0)
			SendMessage(logchan, "Error getting thread IP.")
		if check[0] and check[1] == "tor":
			SendMessage(logchan, "Warning: This thread was made using TOR. Removing thread.")
			MoveThread(threadID, 7)
			LockThread(threadID, "Thread automatically moved and locked because it was posted with TOR")
		elif check[0] and check[1] == "neostrada":
			SendMessage(logchan, "Warning: This thread was made using Neostrada Plus.")
			#MoveThread(threadID, 7)
			#LockThread(threadID, "Thread automatically moved and locked because it was posted from a blacklisted ISP")
		elif check[0]:
			SendMessage(logchan, "Warning: This thread was made from a suspicious IP address.")

		usercheck = CheckUsername(username)
		if usercheck[0] and usercheck[1] == "126.com":
			SendMessage(logchan, "Removing thread due to potential spambot.")
			MoveThread(threadID, 7)
			LockThread(threadID, "Thread automatically moved and locked because it might have come from a spambot")

seenReports = {}
def AlwaysRun(channel):
	global seenReports
	now = datetime.now()
	if now.minute == 30 and now.second == 0:
		reportlist = ReportsList()
		if reportlist == None:
			SendMessage(GetSetting(__name__, "info-chan"), "Error fetching reports")
			return
		reportlistunseen = [report for report in reportlist if seenReports.get(report[1]) != int(report[0])]
		for report in reportlistunseen:
			if seenReports.get(report[1]) and int(report[0]) > int(seenReports.get(report[1])):
				report = (int(report[0]) - int(seenReports.get(report[1])), report[1], report[2])
		if len(reportlist):
			SendMessage(GetSetting(__name__, "info-chan"), u"There are \u0002%s unread reports\u0002: " % (len(reportlist)) + ", ".join(["http://tpt.io/~%s#Reports %s" % (report[1], report[0]) for report in reportlist]))
			PrintReportList(GetSetting(__name__, "info-chan"), reportlistunseen)
		seenReports = {}
		for report in reportlist:
			seenReports[report[1]] = int(report[0])

		#if len(reportlist):
		#	SendMessage(GetSetting(__name__, "info-chan"), "Report list: " + ", ".join(["http://tpt.io/~%s#Reports %s" % (report[1], report[0]) for report in reportlist]))
		#else:
		#	SendMessage(GetSetting(__name__, "info-chan"), "Test: No reports")

		convolist = GetConvoList()
		for convo in convolist:
			SendMessage("jacob1", "Conversation: {0} by {1} ({2} messages)".format(convo["Subject"], convo["MostRecent"], convo["MessageCount"]))
		sleep(1)
	if now.hour == 6 and now.minute == 1 and now.second == 4:
		torlist = GetPage("https://www.dan.me.uk/torlist/")
		if not torlist:
			SendMessage(GetSetting(__name__, "info-chan"), "Error fetching tor list")
			return
		torfile = open("torlist.txt", "w")
		torfile.write(torlist)
		torfile.close()
		SendMessage(GetSetting(__name__, "info-chan"), "Updated list of TOR IPs, there are now %s IPs" % (len(torlist.splitlines())))
	if now.second == 0 and now.minute%10 == 1:
		CheckCommentBans()

scannedcomments = set()
def CheckCommentBans():
	global scannedcomments
	#commentbans = GetData(__name__, "commentbans")
	#if not commentbans:
	#	return
	#commentbansorig = ["Frads_man", "JanKaszanka", "DrBreen"]
	#commentbans = [149086, 156645, 168723]
	usermap = {143701:"DrBrick", 156645:"JanKaszanka", 164702:"troy7838"}
	#commentbans = {"DrBrick":["JanKaszanka","troy7838"], "JanKaszanka":["DrBrick"], "troy7838":["DrBrick"]}
	commentbans = {}
	for user, commentban in commentbans.items():
		userid = -1
		for useri, username in usermap.items():
			if user == username:
				userid = useri
		if userid == -1:
			continue
		comments = GetUserComments(userid, page=0)
		if not comments:
			continue
		for comment in comments:
			if comment[2] in scannedcomments:
				continue
			scannedcomments.add(comment[2])
			if True or re.match(r"^\d{1,2}:\d{1,2}:\d{1,2}$", comment[0]):
				#SendMessage(GetSetting(__name__, "info-chan"), "Recent comment: "+comment[3])
				saveinfo = GetSaveInfo(comment[1])
				if not saveinfo:
					SendMessage(GetSetting(__name__, "info-chan"), "Error getting save info for ID "+comment[1])
					continue
				#SendMessage(GetSetting(__name__, "info-chan"), "Comment is on save {0} by {1}".format(saveinfo["Name"], saveinfo["Username"]))
				if saveinfo["Username"] in commentban:
					DeleteComment(comment[1], comment[2], safe=False)
					SendMessage(GetSetting(__name__, "info-chan"), "Deleted {0}'s comment on {1} by {2}: {3}".format(user, saveinfo["Name"], saveinfo["Username"], comment[3]))
	#SendMessage(GetSetting(__name__, "info-chan"), "comment scan complete")

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
	except ValueError:
		userID = int(GetUserID(username))
	page = GetPage("http://powdertoy.co.uk/User/Moderation.html?ID={0}&PageNum={1}".format(userID, page), GetTPTSessionInfo(0))
	if not page:
		return None
	comments = re.findall("<span class=\"Date\">([^<]+)</span>.*\n.*\n.*\?ID=(\d+)&DeleteComment=(\d+)&.*\n.*\n.*Message\">(.*?)<", page)
	return comments

def GetSaveComments(saveID, page=0):
	page = GetPage("http://powdertoy.co.uk/Browse/View.html?ID={0}&PageNum={1}".format(saveID, page), GetTPTSessionInfo(0))
	comments = re.findall("\/User\.html\?Name=([\w_-]+)\">.*\n.*\n.*\n.*\/Browse\/View\.html\?ID=(\d+)&amp;DeleteComment=(\d+)\".*\n.*\n.*Message\">(.*?)<", page)
	return comments

def DeleteComment(saveID, commentID, safe=True):
	saveComments = GetSaveComments(saveID)
	if safe:
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

def GetEmail(username):
	asdf = GetPage(GetSetting(__name__, "email-url") + "{0}".format("&Name="+username), GetTPTSessionInfo(0))
	parsed = json.loads(asdf)
	userlist = parsed["Users"]
	for user in userlist:
		matches = re.search("User-(\d)\.png.+Moderation\.html\?ID=(\d+)\\\">([^<]+)<.+\\\"Email\\\">([^<]+)<", user)
		usertype = int(matches.group(1))
		username_ = matches.group(3)
		email = matches.group(4)
		if username == username_:
			return email

@command("ban", minArgs = 4, owner = True)
def Ban(message):
	"""(ban <user ID> <ban time> <ban time units> <reason>). bans someone in TPT. Owner only. Add = to ban usernames that look like IDs"""
	if message.nick != "jacob1":
		message.ReplyNotice("Error, only jacob1 should be able to use this command")
	if not BanUser(message.GetArg(0), message.GetArg(1), message.GetArg(2), message.GetArg(3, endLine=True)):
		message.Reply("An error occured while trying to ban user.")

@command("unban", minArgs = 1, owner = True)
def Unban(message):
	"""(unban <user ID>). unbans someone in TPT. Owner only."""
	if message.nick != "jacob1":
		message.ReplyNotice("Error, only jacob1 should be able to use this command")
	if not UnbanUser(message.GetArg(0)):
		message.Reply("An error occured while trying to unban user.")

@command("hide", minArgs = 1, owner = True)
def Hide(message):
	"""(hide <post ID> [<reason>]). Hides a post in TPT. Owner only."""
	if HidePost(message.GetArg(0), False, message.GetArg(1, endLine=True)):
		message.Reply("Done.")
	else:
		message.Reply("Error hiding post.")

@command("remove", minArgs = 1, admin = True)
def Remove(message):
	"""(remove <post ID> [<reason>]). Removes a post in TPT. Admin only."""
	if HidePost(message.GetArg(0), True, message.GetArg(1, endLine=True)):
		message.Reply("Done.")
	else:
		message.Reply("Error hiding post.")

@command("unhide", minArgs = 1, admin = True)
def Unhide(message):
	"""(unhide <post ID>). Unhides a post in TPT. Admin only."""
	if UnhidePost(message.GetArg(0)):
		message.Reply("Done.")
	else:
		message.Reply("Error hiding post.")

@command("lock", minArgs = 2, owner = True)
def Lock(message):
	"""(lock <thread ID> <reason>). Locks a thread in TPT. Owner only."""
	LockThread(message.GetArg(0), message.GetArg(1, endLine=True))
	message.Reply("No output.")

@command("unlock", minArgs = 1, owner = True)
def Unlock(message):
	"""(unlock <thread ID>). Unlocks a thread in TPT. Owner only."""
	UnlockThread(message.GetArg(0))
	message.Reply("No output.")

@command("move", minArgs = 2, admin = True)
def Unlock(message):
	"""(move <thread ID> <new section>). Moves a thread into a new section. Must use forum section IDs, not names. Admin only."""
	MoveThread(message.GetArg(0), message.GetArg(1))
	message.Reply("No output.")

@command("promolevel", minArgs = 2, admin = True)
def Unlock(message):
	"""(promolevel <save ID> <level>). Sets the promotion level on a save. Admin only."""
	if PromotionLevel(message.GetArg(0), int(message.GetArg(1))):
		message.Reply("Done.")
	else:
		message.Reply("Invalid promotion level.")

@command("ipmap", minArgs = 1, admin = True)
def IpMap(message):
	"""(ipmap <username/ip>). Prints out linked accounts or IP addresses. Admin only."""
	message.Reply(GetLinkedAccounts(message.GetArg(0)))

@command("saveinfo", minArgs = 1, admin = True)
def SaveInfo(message):
	"""(saveinfo <saveid>). Prints out lots of useful information about TPT saves. Admin only."""
	info = GetSaveInfoDetailed(message.GetArg(0))
	if info:
		formatted = FormatSaveInfo(info)
		for line in formatted.split("\n"):
			message.Reply(line)
	else:
		message.Reply("Save info not found")

@command("getreports", minArgs=1, admin = True)
def GetReports(message):
	"""(getreports <saveid> [numreports]). Prints out all (or numreports) reports from a save. Admin only."""
	count = None
	reportlist = SaveReports(message.GetArg(0))
	if message.GetArg(1):
		count = int(message.GetArg(1))
	PrintReports(message.channel, reportlist[:count])

@command("markread", minArgs=1, admin = True)
def MarkRead(message):
	"""(markread <saveid>). Marks a report on a save as read. Admin only."""
	GetPage("http://powdertoy.co.uk/Reports.html?Read=%s" % message.GetArg(0), GetTPTSessionInfo(0))
	message.Reply("No output.")

@command("markallread", admin = True)
def MarkAllRead(message):
	"""(markallread). Marks all reports that have been printed to channel previously as read. Admin only."""
	global seenReports
	reportlist = ReportsList()
	if reportlist == None:
		message.Reply("Error fetching reports")
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
		message.Reply("These saves were marked as read: %s" % (" ".join(markedread)))
	if unread:
		message.Reply("These saves still have unread reports: %s" % (" ".join(unread)))

@command("reports", admin = True)
def Reports(message):
	"""(reports) No args. Prints out the reports list. Admin only."""
	global seenReports
	reportlist = ReportsList()
	if reportlist == None:
		message.Reply("Error fetching reports")
		return
	elif len(reportlist) == 0:
		message.Reply("No reports")
	else:
		PrintReportList(message.channel, reportlist)

	seenReports = {}
	for report in reportlist:
		seenReports[report[1]] = report[0]

@command("comment", minArgs=2, admin = True)
def Comment(message):
	"""(comment <saveID> <comment>). Comments on a save as jacobot. Admin only."""
	if DoComment(message.GetArg(0), message.GetArg(1, endLine=True), False):
		message.Reply("Done.")
	else:
		message.Reply("Error, could not comment.")

@command("commentj1", minArgs=2, owner = True)
def Comment(message):
	"""(commentj1 <saveID> <comment>). Comments on a save as jacob1. Owner only."""
	if DoComment(message.GetArg(0), message.GetArg(1, endLine=True), True):
		message.Reply("Done.")
	else:
		message.Reply("Error, could not comment.")

@command("unpublish", minArgs=1, admin = True)
def Unpublish(message):
	"""(unpublish <saveID>). Unpublishes a save. Admin only."""
	DoUnpublish(message.GetArg(0))
	message.Reply("Done.")

@command("publish", minArgs=1, admin = True)
def Publish(message):
	"""(publish <saveID>). Publishes a save. Admin only."""
	DoPublish(message.GetArg(0))
	message.Reply("Done.")

@command("listtags", minArgs=1, admin=True)
def ListTags(message):
	"""(listtags <saveID>). Lists tags on a save. Admin only."""
	PrintTags(message.channel, message.GetArg(0))

@command("showtag", minArgs=1, admin=True)
def ShowTag(message):
	"""(showtag <tag>). Shows where tags have been used. Admin only."""
	data = GetTagUsages(message.GetArg(0))
	if data["count"] > 40:
		usercounts = defaultdict(int)
		for tag in data["usages"]:
			usercounts[tag[1]] = usercounts[tag[1]] + 1
		top = sorted(usercounts.items(), key=lambda a: a[1])[:-30:-1]
		message.Reply("Tag used {0} times, by: {1}".format(data["count"], ", ".join(["{0} x{1}".format(usertag[0], usertag[1]) for usertag in top])))
	else:
		prepend = "http://tpt.io/:" if data["count"] < 20 else ""
		msg = []
		for tag in data["usages"]:
			msg.append("{0}{1} : {2}".format(prepend, tag[0], tag[1]))
		message.Reply("Tag used {0} times. {1}".format(data["count"], ", ".join(msg)))

@command("removetag", minArgs=2, admin=True)
def RemoveTagCmd(message):
	"""(removetag <tag> <saveID>). Removes a tag on a save. Admin only."""
	if RemoveTag(message.GetArg(0), message.GetArg(1)):
		message.Reply("Done.")
	else:
		message.Reply("Error, could not remove tag.")

@command("disabletag", minArgs=1, admin=True)
def DisableTagCmd(message):
	"""(disabletag <tag>). Disables a tag. Admin only."""
	if message.GetArg(1):
		fail = False
		for tag in message.commandLine.split():
			if not DisableTag(tag):
				fail = True
				break
	else:
		fail = DisableTag(message.GetArg(0))
	if not fail:
		message.Reply("Done.")
	else:
		message.Reply("Error, could not disable tag{0}.".format("" if message.GetArg(1) else "s"))

@command("enabletag", minArgs=1, admin=True)
def DisableTagCmd(message):
	"""(enabetag <tag>). Enables a tag. Admin only."""
	if DisableTag(message.GetArg(0), True):
		message.Reply("Done.")
	else:
		message.Reply("Error, could not disable tag.")

@command("bannedtags", minArgs = 1, admin = True)
def Bannedtags(message):
	"""(bannedtags add <tagregex>|remove <tagregex>|list). Modifies the banned tag regex list. Admin only."""
	bannedtags = GetData(__name__, "bannedtags")
	if not bannedtags:
		bannedtags = []
	if message.GetArg(0).lower() == "list":
		if not bannedtags:
			message.Reply("No banned tag regexes")
		else:
			message.Reply("Banned tag regexes: " + ", ".join(bannedtags))
		return
	action = message.GetArg(0).lower()
	if action == "remove":
		if message.GetArg(1) not in bannedtags:
			message.Reply("That tag regex isn't currently banned")
		else:
			bannedtags.remove(message.GetArg(1))
			StoreData(__name__, "bannedtags", bannedtags)
			message.Reply("Removed %s from the banned tag regex list" % message.GetArg(1))
	elif action == "add":
		if message.GetArg(1) in bannedtags:
			message.Reply("That tag regex is already banned")
		else:
			bannedtags.append(message.GetArg(1))
			StoreData(__name__, "bannedtags", bannedtags)
			message.Reply("Added %s to the banned tag regex list" % message.GetArg(1))
	else:
		message.Reply("Unknown action")

@command("readreport", minArgs=2, admin = True)
def Stolen(message):
	"""(readreport <saveID> <comment>). Disables a save and comments with a message as jacobot. Admin only."""
	saveID = message.GetArg(0)
	#DoUnpublish(saveID)
	ret = PromotionLevel(saveID, -2)
	if ret:
		print("test", message.GetArg(1, endLine=True))
		ret = DoComment(saveID, message.GetArg(1, endLine=True))
		if ret:
			message.Reply("Done.")
		else:
			message.Reply("Error, could not comment.")
	else:
		message.Reply("Error, could not disable save.")

@command("copied", minArgs=2, admin = True)
def Copied(message):
	"""(copied <copiedID> <originalID> [--override] [<reason>]). Unpublishes a save and leaves a comment by jacobot with the original saveID, save name, and author. Optional message can be appended to the end. Admin only."""
	stolenID = message.GetArg(0)
	saveID = message.GetArg(1)
	argpos = 2
	override = False
	if message.GetArg(2) == "--override":
		override = True
		argpos = 3
	try:
		if int(stolenID) <= int(saveID) and not override:
			message.Reply("Error: stolenID can't be less than originalID. Use --override to force.")
			return
	except ValueError:
		message.Reply("Error: saveIDs must be integers")
		return
	if not DoUnpublish(stolenID):
		message.Reply("Error unpublishing save.")
		return
	info = GetSaveInfo(saveID)
	if info:
		msg = "Save unpublished: copied without credit from id:%s (save \"%s\" by %s)." % (saveID, info["Name"], info["Username"])
		if message.GetArg(argpos):
			msg = "%s %s" % (msg, message.GetArg(argpos, endLine=True))
		else:
			msg = msg + " Please give credit to the original owner when modifying saves."
		if DoComment(stolenID, msg):
			message.Reply("Done.")
		else:
			message.Reply("Error commenting.")
	else:
		message.Reply("Error getting original save info.")

@command("stolen", minArgs=2, admin = True)
def Stolen(message):
	"""(stolen <stolenID> <originalID> [--override] [<reason>]). Disables a save and leaves a comment by jacobot with the original saveID, save name, and author. Optional message can be appended to the end, or 'long' for default optional message. Admin only."""
	stolenID = message.GetArg(0)
	saveID = message.GetArg(1)
	argpos = 2
	override = False
	if message.GetArg(2) == "--override":
		override = True
		argpos = 3
	try:
		if int(stolenID) <= int(saveID) and not override:
			message.Reply("Error: stolenID can't be less than originalID.")
			return
	except ValueError:
		message.Reply("Error: saveIDs must be integers")
		return
	if not PromotionLevel(stolenID, -2):
		message.Reply("Error unpublishing save.")
		return
	info = GetSaveInfo(saveID)
	if info:
		msg = "Save unpublished: stolen from id:%s (save \"%s\" by %s)." % (saveID, info["Name"], info["Username"])
		if message.GetArg(argpos):
			msg += " " + message.GetArg(argpos, endLine=True)
		if DoComment(stolenID, msg):
			message.Reply("Done.")
		else:
			message.Reply("Error commenting.")
	else:
		message.Reply("Error getting original save info.")

@command("updatetor", admin = True)
def UpdateTor(message):
	"""(no args). Update the list of TOR ip addresses. Admin only."""
	torlist = GetPage("https://www.dan.me.uk/torlist/")
	if not torlist:
		message.Reply("Error fetching tor list")
		return
	torfile = open("torlist.txt", "w")
	torfile.write(torlist)
	torfile.close()
	message.Reply("Updated list of TOR IPs, there are now %s IPs" % (len(torlist.splitlines())))

@command("ipban", minArgs = 1, admin = True)
def IPban(message):
	"""(ipban add <ip>|remove <ip>|mark <ip> <reason>|makrperm <ip> list). Modifies the IP bans list. Admin only."""
	ipbans = GetData(__name__, "ipbans")
	if not ipbans:
		ipbans = {}
	if message.GetArg(0).lower() == "list":
		if not ipbans:
			message.Reply("Nobody is currently IP banned")
		else:
			output = "List of currently banned IPs: {0}"
			infolist = []
			for IP, info in ipbans.items():
				expireStr = datetime.utcfromtimestamp(info["expires"]).strftime("%Y-%m-%dT%H:%M:%SZ") if info["expires"] else "never"
				infolist.append("{0} ({1}, expires {2})".format(IP, info["reason"], expireStr))
			message.Reply(output.format(", ".join(infolist)))
	elif message.GetArg(1):
		action = message.GetArg(0).lower()
		IP = message.GetArg(1)
		if action == "add":
			if IP in ipbans:
				message.Reply("{0} is already in the IP ban list".format(IP))
			else:
				expireTime = int(time.time()+timedelta(days=30).total_seconds())
				info = {"reason":"no reason given", "expires":expireTime}
				ipbans[IP] = info
				message.Reply("Added {0} to the IP ban list".format(IP))
		elif IP not in ipbans:
			message.Reply("{0} isn't in the IP ban list".format(IP))
		elif action == "remove":
			del ipbans[IP]
			message.Reply("Removed {0} from the IP ban list".format(IP))
		elif action == "mark" and message.GetArg(2):
			ipbans[IP]["reason"] = message.GetArg(2, endLine=True)
			message.Reply("Done.")
		elif action == "makeperm":
			ipbans[IP]["expires"] = None
			message.Reply("Done.")
		else:
			message.Reply("Unknown action")
		StoreData(__name__, "ipbans", ipbans)
	else:
		message.Reply("Unknown action")

@command("getusercomments", minArgs=1, owner = True)
def GetUserCommentsCmd(message):
	"""(getusercomments <userID/username> [<pagenumber>]). Debug command to print comments by a certain user. Owner only."""
	message.Reply(str(GetUserComments(message.GetArg(0), message.GetArg(1) if message.GetArg(1) else 0)))

@command("getsavecomments", minArgs=1, owner = True)
def GetSaveCommentsCmd(message):
	"""(getsavecomments <saveID> [<pagenum>]). Debug command to print comments on a save. Owner only."""
	message.Reply(str(GetSaveComments(message.GetArg(0), message.GetArg(1) if message.GetArg(1) else 0)))

@command("deleteusercomments", minArgs=1, admin=True)
def DeleteUserCommentsCmd(message):
	"""(deleteusercomments <userID/username> [<pagenumber>]). Deletes all comments by a user on a certain page (as long as the comments are the most recent comments on their respective saves). Admin only."""
	pagenum = message.GetArg(1) if message.GetArg(1) else 0
	try:
		if int(pagenum) < 0:
			message.Reply("Error: pagenum must be a positive integer")
			return
	except ValueError:
		message.Reply("Error: pagenum must be a positive integer")
		return
	comments = GetUserComments(message.GetArg(0), message.GetArg(1) if message.GetArg(1) else 0)
	if not comments:
		message.Reply("Error: user does not exist")
		return
	for comment in comments:
		if not DeleteComment(comment[1], comment[2], safe=True):
			message.Reply("Error deleting comment #{0} on ID:{1}".format(comment[2], comment[1]))
			break
	message.Reply("Done.")

@command("getpostip", minArgs=1, admin=True)
def GetPostIPCmd(message):
	"""(getpostip <postID>). Returns the IP used to make a forum post. Admin only."""
	postIP = GetPostIP(message.GetArg(0))
	if postIP:
		suspicious, reason = CheckIP(postIP)
		if suspicious:
			message.Reply("{0}: this IP is in the {1} blacklist".format(postIP, reason))
		else:
			message.Reply(postIP)
	else:
		message.Reply("Error: Could not get IP")

@command("getthreadpostip", minArgs=1, admin=True)
def GetThreadPostIPCmd(message):
	"""(getthreadpostip <postID>). Returns the IP used to make a forum thread. Admin only."""
	threadIP = GetThreadPostIP(message.GetArg(0))
	if threadIP:
		message.Reply(threadIP)
	else:
		message.Reply("Error: Could not get IP")

@command("checkforumspam", minArgs=1, admin=True)
def CheckForumSpamCmd(message):
	"""(checkforumspam <ip>). Checks stopforumspam.org for possible forum spam."""
	data = CheckForumSpam(message.GetArg(0))
	ip = data.get("ip", {})
	confidence = ip.get("confidence", "[none]")
	lastseen = ip.get("lastseen", "[none]")
	frequency = ip.get("frequency", "[none]")
	output = "{0} chance of being a spammer. Last seen {1}. Appears {2} times".format(confidence, lastseen, frequency)
	message.Reply(output)

@command("getemailraw", owner=True)
def GetEmailRawCmd(message):
	"""(getemailraw [Name=<name>] [Email=<email>] [<PageNum>]). Searches for an email by username or email."""

	searchArgs = []
	pageNum = 0
	args = message.commandLine.split()
	for arg in args:
		try:
			(name, value) = arg.split("=")
			if name.lower() == "name":
				searchArgs.append("&Name="+value)
			elif name.lower() == "email":
				searchArgs.append("&Email="+value)
			else:
				raise ShowHelpException()
		except ValueError:
			try:
				int(arg)
				searchArgs.append("&PageNum="+arg)
			except ValueError:
				raise ShowHelpException()

	asdf = GetPage(GetSetting(__name__, "email-url") + "{0}".format("".join(searchArgs)), GetTPTSessionInfo(0))
	parsed = json.loads(asdf)
	userlist = parsed["Users"]
	colorlist = ["", "04", "11", "13", "08"]
	outputlist = []
	for user in userlist:
		matches = re.search("User-(\d)\.png.+Moderation\.html\?ID=(\d+)\\\">([^<]+)<.+\\\"Email\\\">([^<]+)<", user)
		usertype = int(matches.group(1))
		username = matches.group(3)
		email = matches.group(4)
		if colorlist[usertype]:
			username = "\x03{0}{1}\x03".format(colorlist[usertype], username)
		outputlist.append("{0}: {1}".format(username, email))
	if not outputlist:
		message.Reply("No results")
	else:
		output = ", ".join(outputlist)
		if len(outputlist) > 12 and len(output) >= 480:
			message.Reply(", ".join(outputlist[:12]))
			message.Reply(", ".join(outputlist[13:]))
		else:
			message.Reply(output)

@command("getemail", minArgs=1, admin=True)
def GetEmailCmd(message):
	"""(getemail <username>). Gets email by username."""
	username = message.GetArg(0)
	email = GetEmail(username)
	message.Reply(email if email else "email not found")

