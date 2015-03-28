import urllib, urllib2
import json
import time
from common import *
RegisterMod(__name__)

ipbans = ("[213.149.187.164]",)
def Parse(raw, text):
    if len(text) >= 8 and text[0] == ":StewieGriffin!~Stewie@Powder/Bot/StewieGriffin" and text[1] == "PRIVMSG" and text[2] == "#powder-info" and text[3] == ":New" and text[4] == "registration:":
        if text[7] in ipbans:
            BanUser(text[5][:-1], "1", "p", "Automatic ip ban")

#Generic useful functions
def GetTPTSessionInfo(line):
    with open("passwords.txt") as f:
        return f.readlines()[line].strip()

def GetUserID(username):
	page = GetPage("http://powdertoy.co.uk/User.json?Name={}".format(username))
	thing = page.find("\"ID\":")
	return page[thing+5:page.find(",", thing)]

#Ban / Unban Functions
def BanUser(username, time, timeunits, reason):
    try:
        userID = int(username)
    except:
        userID = GetUserID(username)
    if userID < 0 or userID == 1 or userID == 38642:
        return
    data = {"BanUser":str(userID).strip("="), "BanReason":reason, "BanTime":time, "BanTimeSpan":timeunits}
    GetPage("http://powdertoy.co.uk/User/Moderation.html?ID=%s&Key=%s" % (userID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), data)

def UnbanUser(userID):
    try:
        userID = int(username)
    except:
        userID = GetUserID(username)
    if userID < 0:
	    return
    data = {"UnbanUser":str(userID).strip("=")}
    GetPage("http://powdertoy.co.uk/User/Moderation.html?ID=%s&Key=%s" % (userID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), data)

#Functions to get info from TPT
def GetPostInfo(postID):
    page = GetPage("http://tpt.io/.%s" % postID)
    match = re.search("<div class=\"Comment\">(.+?<div id=\"MessageContainer-%s\" class=\"Message\">.+?)</li>" % postID, page, re.DOTALL)
    matchinfo = filter(None, re.split("[ \n\t]*<.+?>[ \n\t]*", match.group(1)))
    #"[ \n\t]*</?div.+?>[ \n\t+]*"
    print(matchinfo)

def GetSaveInfo(saveID):
    page = GetPage("http://powdertoythings.co.uk/Powder/Saves/ViewDetailed.json?ID=%s" % saveID)
    info = json.loads(page)
    return info

def FormatDate(unixtime):
    timestruct = time.localtime(unixtime)
    strftime = time.strftime("%a %b %d %Y %I:%M:%S%p", timestruct)
    return strftime

def FormatSaveInfo(info):
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
    data = {"Hide_Reason":reason}
    if remove:
        data["Hide_Remove"] = "1"
    GetPage("http://powdertoy.co.uk/Discussions/Thread/HidePost.html?Post=%s&Key=%s" % (postID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0), data)

def UnhidePost(postID):
    GetPage("http://powdertoy.co.uk/Discussions/Thread/UnhidePost.html?Post=%s&Key=%s" % (postID, GetTPTSessionInfo(1)), GetTPTSessionInfo(0))

def LockThread(threadID, reason):
    GetPage("http://powdertoy.co.uk/Discussions/Thread/Moderation.html?Thread=%s" % (threadID), GetTPTSessionInfo(0), {"Moderation_Lock":"Lock Thread", "Moderation_LockReason":reason})

def UnlockThread(threadID):
    GetPage("http://powdertoy.co.uk/Discussions/Thread/Moderation.html?Thread=%s" % (threadID), GetTPTSessionInfo(0), {"Moderation_Unlock":"Unlock"})

def GetLinkedAccounts(account):
    try:
        if account.find(".") >= 0:
            page = GetPage("http://powdertoy.co.uk/IPTools/GetInfo.json?IP=%s" % account, GetTPTSessionInfo(0))
        else:
            page = GetPage("http://powdertoy.co.uk/IPTools/GetInfo.json?Username=%s" % account, GetTPTSessionInfo(0))
    except:
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

@command("ban", minArgs = 4, owner = True)
def Ban(username, hostmask, channel, text, account):
    """(ban <user ID> <ban time> <ban time units> <reason>). bans someone in TPT. Owner only. Add = to ban usernames that look like IDs"""
    if username != "jacob1":
        SendNotice(username, "Error, only jacob1 should be able to use this command")
    BanUser(text[0], text[1], text[2], " ".join(text[3:]))

@command("unban", minArgs = 1, owner = True)
def Unban(username, hostmask, channel, text, account):
    """(unban <user ID>). unbans someone in TPT. Owner only."""
    if username != "jacob1":
        SendNotice(username, "Error, only jacob1 should be able to use this command")
    UnbanUser(text[0])

@command("post", minArgs = 1, owner = True)
def Post(username, hostmask, channel, text, account):
    """(post <post ID>). Gets info on a TPT post."""
    GetPostInfo(text[0])
    
@command("hide", minArgs = 1, owner = True)
def Hide(username, hostmask, channel, text, account):
    """(hide <post ID> [<reason>]). Hides a post in TPT. Owner only."""
    HidePost(text[0], False, " ".join(text[1:]))

@command("remove", minArgs = 1, owner = True)
def Remove(username, hostmask, channel, text, account):
    """(remove <post ID> [<reason>]). Removes a post in TPT. Owner only."""
    HidePost(text[0], True, " ".join(text[1:]))

@command("unhide", minArgs = 1, owner = True)
def Unhide(username, hostmask, channel, text, account):
    """(unhide <post ID>). Unhides a post in TPT. Owner only."""
    UnhidePost(text[0])

@command("lock", minArgs = 2, owner = True)
def Lock(username, hostmask, channel, text, account):
    """(lock <thread ID> <reason>). Locks a thread in TPT. Owner only."""
    LockThread(text[0], " ".join(text[1:]))

@command("unlock", minArgs = 1, owner = True)
def Unlock(username, hostmask, channel, text, account):
    """(unlock <thread ID>). Unlocks a thread in TPT. Owner only."""
    UnlockThread(text[0])

@command("ipmap", minArgs = 1, owner = True)
def IpMap(username, hostmask, channel, text, account):
    """(ipmap <username/ip>). Prints out linked accounts or IP addresses. Owner only."""
    SendMessage(channel, GetLinkedAccounts(text[0]))

@command("saveinfo", minArgs = 1, owner = True)
def SaveInfo(username, hostmask, channel, text, account):
    """(saveinfo <saveid>). Prints out lots of useful information about TPT saves. Owner only."""
    info = GetSaveInfo(text[0])
    formatted = FormatSaveInfo(info)
    for line in formatted.split("\n"):
        SendMessage(channel, line)
