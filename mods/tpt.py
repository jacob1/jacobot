import urllib, urllib2
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

#Not TPT, temporary
@command("iam", owner = True)
def Remove(username, hostmask, channel, text, account):
    """(iam <text>). Submits text to iam's game thing. Owner only."""
    GetPage("http://173.206.82.2/game/sendtext.php", {"message":" ".join(text)}, {"message":" ".join(text)})


