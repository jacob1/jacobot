import urllib, urllib2
import json
from common import *
RegisterMod(__name__)

def Parse(raw, text):
    if len(text) >= 8 and text[0] == ":StewieGriffin!~Stewie@Powder/Bot/StewieGriffin" and text[1] == "PRIVMSG" and text[2] == "#powder-info" and text[3] == ":New" and text[4] == "registration:":
        if text[7] == "[82.171.135.245]":
            BanUser(text[5][:-1], "1", "p", "Automatic ip ban (if placed in error, please contact jacob1)")

def GetTPTSessionInfo(line):
    with open("passwords.txt") as f:
        return f.readlines()[line].strip()

def GetUserID(username):
	page = GetPage("http://powdertoy.co.uk/User.json?Name={}".format(username))
	thing = page.find("\"ID\":")
	return page[thing+5:page.find(",", thing)]

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

def GetPostInfo(postID):
    page = GetPage("http://tpt.io/.%s" % postID)
    match = re.search("<div class=\"Comment\">(.+?<div id=\"MessageContainer-%s\" class=\"Message\">.+?)</li>" % postID, page, re.DOTALL)
    matchinfo = filter(None, re.split("[ \n\t]*<.+?>[ \n\t]*", match.group(1)))
    #"[ \n\t]*</?div.+?>[ \n\t+]*"
    print(matchinfo)

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
