import socket
import select
import traceback
from time import sleep
import os
import atexit
import imp

if not os.path.isfile("config.py"):
    import shutil
    shutil.copyfile("config.py.default", "config.py")
    print("config.py.default copied to config.py")
execfile("config.py")
if not configured:
    print("you have not configured the bot, open up config.py to edit settings")
    quit()

from common import *
mods = {}
for i in os.listdir("mods"):
    if os.path.isfile(os.path.join("mods", i)) and i[-3:] == ".py":
        mods[i[:-3]] = imp.load_source(i[:-3], os.path.join("mods", i))

def Connect():
    global irc
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.connect((server,6667))
    irc.setblocking(0)
    irc.send("USER %s %s %s :%s\n" % (botIdent, botNick, botNick, botRealname))
    irc.send("NICK %s\n" % botNick)
    if NickServ:
        irc.send("PRIVMSG NickServ :identify %s %s\n" % (botAccount, botPassword))
    else:
        irc.send("JOIN %s\n" % channel)
    sleep(7)

def ReadPrefs():
    with open('logins.txt') as f:
        for line in f:
            if len(line.strip()):
                cookies = line.split("|")
                logins[cookies[0]] = {"username":cookies[1], "portfolio":{}, "cookies":cookies[2].strip()}

def WritePrefs():
    with open('logins.txt', 'w') as f:
        for i in logins:
            f.write("%s|%s|%s\r\n" % (i, logins[i]["username"], logins[i]["cookies"]))
atexit.register(WritePrefs)

def PrintError(channel = None):
    print "=======ERROR=======\n%s========END========\n" % (traceback.format_exc())
    if channel:
        irc.send("PRIVMSG %s :Error printed to console\n" % (channel))
    
def Interrupt():
    irc.send("QUIT :Keyboard Interrupt\n")
    irc.close()
    quit()

def main():
    while True:
        try:
            line = ""
            ready = select.select([irc], [], [], 1.0)
            if ready[0]:
                line = irc.recv(2040)
        except KeyboardInterrupt:
            Interrupt()
        except: #socket.error, e:   or   socket.timeout, e:
            PrintError()
            return
        else:
            if len(line):
                try:
                    if ":!!login" in line:
                        print("<someone logging in>")
                    else:
                        print(line)
                    text = line.split()

                    if len(text) > 0:
                        #Reply to server pings
                        if text[0] == "PING":
                            irc.send("PONG %s\n" % text[1])

                    if len(text) > 1:
                        #Only join channel once identified
                        if text[1] == "396":
                            irc.send("JOIN %s\n" % channel)

                    if len(text) > 2:
                        #Get channel to reply to
                        if text[1] == "PRIVMSG":
                            reply = text[2]
                            if reply == botNick:
                                reply = text[0].split("!")[0].lstrip(":")

                    if len(text) >= 4:
                        #Parse line in stocks.py
                        if len(text):
                            Parse(text)
                except KeyboardInterrupt:
                    Interrupt()
                except SystemExit:
                    irc.send("QUIT :i'm a potato\n")
                    irc.close()
                    quit()
                except:
                    PrintError(reply)
        try:
            mods["stocks"].AlwaysRun(channel)
            #TODO: maybe proper rate limiting, but this works for now
            for i in messageQueue:
                irc.send(i)
            messageQueue[:] = []
        except KeyboardInterrupt:
            Interrupt()
        except:
            PrintError(channel)

def Parse(text):
    if text[1] == "PRIVMSG":
        channel = text[2]
        username = text[0].split("!")[0].lstrip(":")
        hostmask = text[0].split("!")[1]
        command = text[3].lower().lstrip(":")
        if channel == botNick:
            channel = username

        #some special owner commands that aren't in modules
        if CheckOwner(text[0]):
            if command == "!!reload":
                if len(text) <= 4:
                    SendNotice(username, "No module given")
                    return
                mod = text[4]
                if not os.path.isfile(os.path.join("mods", mod+".py")):
                    return
                commands[mod] = []
                if mod == "stocks":
                    logins = mods["stocks"].logins
                    history = mods["stocks"].history
                    watched = mods["stocks"].watched
                    news = mods["stocks"].news
                    specialNews = mods["stocks"].specialNews
                mods[mod] = imp.load_source(mod, os.path.join("mods", mod+".py"))
                if mod == "stocks":
                    mods["stocks"].logins = logins
                    mods["stocks"].history = history
                    mods["stocks"].watched = watched
                    mods["stocks"].news = news
                    mods["stocks"].specialNews = specialNews
                SendMessage(channel, "Reloaded %s.py" % mod)
                return
            elif command == "!!eval":
                try:
                    ret = str(eval(" ".join(text[4:])))
                except Exception as e:
                    ret = str(type(e))+":"+str(e)
                SendMessage(channel, ret)
                return
            elif command == "!!exec":
                try:
                    exec(" ".join(text[4:]))
                except Exception as e:
                    SendMessage(channel, str(type(e))+":"+str(e))
                return
            elif command == "!!quit":
                quit()

        #actual commands here
        for mod in commands:
            for i in commands[mod]:
                if command == "!!"+i[0]:
                    i[1](username, hostmask, channel, text[4:])
                    return

Connect()
mods["stocks"].GetStockInfo(True)
ReadPrefs()
while True:
    main()
    Connect()
