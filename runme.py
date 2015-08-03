import socket
import select
import traceback
from time import sleep
import os
import atexit
import imp
import hashlib
import random

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
    if os.path.isfile(os.path.join("mods", i)) and i[-3:] == ".py" and i[:-3] not in config.disabledPlugins:
        mods[i[:-3]] = imp.load_source(i[:-3], os.path.join("mods", i))

def Connect():
    global irc
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.connect((server,6667))
    irc.setblocking(0)
    irc.send("USER %s %s %s :%s\n" % (botIdent, botNick, botNick, botRealname))
    irc.send("NICK %s\n" % botNick)
    if NickServ:
        irc.send("ns identify %s %s\n" % (botAccount, botPassword))
    else:
        for i in channels:
            irc.send("JOIN %s\n" % i)
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
        if channel[0] != "#":
            channel = channels[0]
        irc.send("PRIVMSG %s :Error printed to console\n" % (channel))
    
def Interrupt():
    irc.send("QUIT :Keyboard Interrupt\n")
    irc.close()
    quit()

def main():
    while True:
        try:
            lines = ""
            ready = select.select([irc], [], [], 1.0)
            if ready[0]:
                lines = irc.recv(2040)
        except KeyboardInterrupt:
            Interrupt()
        except: #socket.error, e:   or   socket.timeout, e:
            PrintError()
            return
        else:
            for line in lines.splitlines():
                try:
                    if ":!!login" in line:
                        print("<someone logging in>\n")
                    else:
                        print(line+"\n")
                    text = line.split()

                    if len(text) > 0:
                        #Reply to server pings
                        if text[0] == "PING":
                            irc.send("PONG %s\n" % text[1])
                        elif text[0] == "ERROR":
                            irc.close()
                            return #try to reconnect

                    if len(text) > 1:
                        #Only join channel once identified
                        if text[1] == "396":
                            for i in channels:
                                irc.send("JOIN %s\n" % i)
                        #Nickname already in use
                        elif text[1] == "433":
                            irc.send("NICK %s-\n" % text[3])
                            if NickServ:
                                irc.send("ns identify %s %s\n" % (botAccount, botPassword))
                                irc.send("ns ghost %s\n" % (botNick))
                                irc.send("NICK %s\n" % (botNick))

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

                    if len(text) >= 5:
                        if text[1] == "MODE" and text[2] == "##powder-bots" and text[3] == "+o" and text[4] == botNick:
                            irc.send("MODE ##powder-bots -o %s\n" % (botNick))

                    #allow modules to do their own text parsing if needed, outside of raw commands
                    for mod in mods:
                         if hasattr(mods[mod], "Parse"):
                            mods[mod].Parse(line, text)
                except KeyboardInterrupt:
                    Interrupt()
                except SystemExit:
                    irc.send("QUIT :i'm a potato\n")
                    irc.close()
                    quit()
                except:
                    PrintError(reply)
        try:
            #allow modules to have a "tick" function constantly run, for any updates they need
            for mod in mods:
                if hasattr(mods[mod], "AlwaysRun"):
                    mods[mod].AlwaysRun(channels[0])
            #TODO: maybe proper rate limiting, but this works for now
            for i in messageQueue:
                irc.send(i)
            messageQueue[:] = []
        except KeyboardInterrupt:
            Interrupt()
        except:
            PrintError(channels[0])

def Parse(text):
    if text[1] == "PRIVMSG":
        channel = text[2]
        username = text[0].split("!")[0].lstrip(":")
        hostmask = text[0].split("!")[1]
        command = text[3].lower().lstrip(":")
        if channel == botNick:
            channel = username
        #if username == "FeynmanStockBot":
        #    return

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

try:
    mods["stocks"].GetStockInfo(True)
except:
    pass
ReadPrefs()
while True:
    try:
        Connect()
        main()
        sleep(20)
    except KeyboardInterrupt:
        break
    except SystemExit:
        break
    except:
        pass
