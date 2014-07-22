import re
from common import *
RegisterMod(__name__)

def GetUsername(who):
    account = GetAccount(ownerHostmask)
    if not account:
        return
    
    page = GetPage("http://tptapi.com/profile_search.php?process", account["cookies"], {"username":who})
    name = re.findall(r"/u/([^']*)'/", page)
    if not name:
        try:
            return str(int(who))
        except:
            return -1
    return name[0]
	
def GetFriends(who):
    account = GetAccount(ownerHostmask)
    if not account:
        return
    who = GetUsername(who)
    if who == -1:
        return "Invalid profile ID"
    page = GetPage("http://tptapi.com/u/" + who, account["cookies"])
    
    name = re.findall(r"<span>([^<>]*)</span>", page)
    if not name:
        return "User does not exist"

    name = name[0]
    friends = []
    friends.extend(re.findall("<b>([^<>]*)</b>", page))
    friends.pop(0)
    friendids = []
    friendids.extend(re.findall(r"/u/([^']*)' ", page))
    friendlist = []
    print(friends, friendids)
    for i in range(len(friends)):
        friendlist.append(friends[i] + " (" + friendids[i] + ")")
    if len(friends):
        return "%s is friends with: %s" % (name, ", ".join(friendlist))
    else:
        if name == "jacob1":
            return "%s is friends with every single person in the world" % name
        else:
            return "%s has no friends!" % name

#http://tptapi.com/friend_request.php?opt=1&id=28&dec=1
def Message(account, who, message):
    who = GetUsername(who)
    if who == -1:
        return "Invalid profile ID"
    
    GetPage("http://tptapi.com/chat_send.php?user=%s" % (who), account["cookies"], {"message":message})
    return "Message sent"

def ReadChat(account, who):
    who = GetUsername(who)
    if who == -1:
        return "Invalid profile ID"
    
    page = GetPage("http://tptapi.com/chat_message.php?id=%s" % (who), account["cookies"]).split("<p>")[1:6]
    if not len(page):
        return "Empty conversation"
    return page

#groups
@command("friends", minArgs = 1)
def FriendsCmd(username, hostmask, channel, text, account):
    """(friends <username|userID>). Returns all the friends of a certain user"""
    SendMessage(channel, GetFriends(text[0]))

@command("message", minArgs = 2)
def MessageCmd(username, hostmask, channel, text, account):
    """(message <username|userID> <text>). Send a message to a user, if you are friends"""
    SendMessage(channel, Message(account, text[0], " ".join(text[1:])))

@command("readchat", minArgs = 1)
def ReadChatCmd(username, hostmask, channel, text, account):
    """(readchat <username|userID>). Print out the last 5 chat messages from your conversation with a user"""
    page = ReadChat(account, text[0])
    for i in page:
        SendMessage(channel, re.sub("<.*?>", "", i))
