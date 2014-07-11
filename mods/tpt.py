import urllib, urllib2
from common import *
RegisterMod(__name__)

def GetTPTSessionInfo(line):
    with open("passwords.txt") as f:
        return f.readlines()[line].strip()

def Ban(userID, time, timeunits, reason):
    if userID == "1" or userID == "38642":
        return
    data = urllib.urlencode({"BanUser":userID, "BanReason":reason, "BanTime":time, "BanTimeSpan":timeunits})
    headers = {'Cookie':GetTPTSessionInfo(0)}
    req = urllib2.Request("http://powdertoy.co.uk/User/Moderation.html?ID=%s&Key=%s" % (userID, GetTPTSessionInfo(1)), data, headers)
     
    response = urllib2.urlopen(req)
    page = response.read()
    #print(page)

def Unban(userID):
    data = urllib.urlencode({"UnbanUser":userID})
    headers = {'Cookie':GetTPTSessionInfo(0)}
    req = urllib2.Request("http://powdertoy.co.uk/User/Moderation.html?ID=%s&Key=%s" % (userID, GetTPTSessionInfo(1)), data, headers)
     
    response = urllib2.urlopen(req)
    page = response.read()
    #print(page)

@command("ban", minArgs = 4, owner = True)
def BanCmd(username, hostmask, channel, text, account):
    """(ban <user ID> <ban time> <ban time units> <reason>). bans someone in TPT. Admin only."""
    if username != "jacob1":
        SendNotice(username, "Error, only jacob1 should be able to use this command")
    Ban(text[0], text[1], text[2], " ".join(text[3:]))

@command("unban", minArgs = 1, owner = True)
def UnbanCmd(username, hostmask, channel, text, account):
    """(unban <user ID>). unbans someone in TPT. Admin only."""
    if username != "jacob1":
        SendNotice(username, "Error, only jacob1 should be able to use this command")
    Unban(text[0])
