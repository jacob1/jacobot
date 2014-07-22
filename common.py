import urllib, urllib2
import re

execfile("config.py")

def CheckOwner(hostmask):
    host = hostmask.split("!")[-1]
    return host == ownerHostmask

#only used for stocks.py, maybe for more later
logins = {}
def GetAccount(hostmask):
    return logins[hostmask] if hostmask in logins else None

messageQueue = []
def Send(msg):
    print("> %s" % msg)
    messageQueue.append(msg)

def SendMessage(target, msg):
    Send("PRIVMSG %s :%s\n" % (target, msg))

def SendNotice(target, msg):
    Send("NOTICE %s :%s\n" % (target, msg))

plugin = ""
def RegisterMod(name):
    global plugin
    commands[name] = []
    plugin = name

commands = {}
def command(name, minArgs = 0, needsAccount = False, owner = False):
    def real_command(func):
        def call_func(username, hostmask, channel, text):
            if owner and not CheckOwner(hostmask):
                SendNotice(username, "This command is owner only")
                return
            if len(text) < minArgs:
                SendNotice(username, "Usage: %s" % func.__doc__)
                return
            account = GetAccount(hostmask)
            if needsAccount and not account:
                SendNotice(username, "You are not logged in")
                return
            return func(username, hostmask, channel, text, account)
        call_func.__doc__ = func.__doc__
        commands[plugin].append((name, call_func))
        return call_func
    return real_command

def GetPage(url, cookies = None, headers = None, removeTags = False):
    if cookies:
        req = urllib2.Request(url, urllib.urlencode(headers) if headers else None, {'Cookie':cookies})
    else:
        req = urllib2.Request(url)
    page = urllib2.urlopen(req, timeout=5).read()
    if removeTags:
        return re.sub("<.*?>", "", page)
    return page
