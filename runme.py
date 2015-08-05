import socket
import select
import traceback
from time import sleep
import os
import sys
import atexit
import imp
import hashlib
import random

if sys.version_info < (3, 0):
    print('Python 3 is required to run the bot.')
    quit()

if not os.path.isfile("config.py"):
    import shutil
    shutil.copyfile("config.py.default", "config.py")
    print("config.py.default copied to config.py")
from config import *
if not configured:
    print("you have not configured the bot, open up config.py to edit settings")
    quit()

from common import *
mods = {}
for i in os.listdir("mods"):
    if os.path.isfile(os.path.join("mods", i)) and i[-3:] == ".py" and i[:-3] not in disabledPlugins:
        try:
            mods[i[:-3]] = imp.load_source(i[:-3], os.path.join("mods", i))
        except Exception:
            pass

def SocketSend(socket, message):
    socket.send(message.encode('utf-8'))

def Print(message):
    if encoding != "utf-8":
        message = message.encode("utf-8").decode(encoding)
    print(message)

def Connect():
    global irc
    Print("Connecting to %s..." % (server))
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.connect((server,6667))
    irc.setblocking(0)
    SocketSend(irc, "USER %s %s %s :%s\n" % (botIdent, botNick, botNick, botRealname))
    SocketSend(irc, "NICK %s\n" % (botNick))
    if NickServ:
        SocketSend(irc, "ns identify %s %s\n" % (botAccount, botPassword))
    else:
        for i in channels:
            SocketSend(irc, "JOIN %s\n" % (i))

def ReadPrefs():
    try:
        with open('logins.txt') as f:
            for line in f:
                if len(line.strip()):
                    cookies = line.split("|")
                    logins[cookies[0]] = {"username":cookies[1], "portfolio":{}, "cookies":cookies[2].strip()}
    except OSError:
        pass

def WritePrefs():
    try:
        with open('logins.txt', 'w') as f:
            for i in logins:
                f.write("%s|%s|%s\r\n" % (i, logins[i]["username"], logins[i]["cookies"]))
    except OSError:
        pass
atexit.register(WritePrefs)

def PrintError(channel = None):
    Print("=======ERROR=======\n%s========END========\n" % (traceback.format_exc()))
    if channel:
        if channel[0] != "#":
            channel = channels[0]
        SocketSend(irc, "PRIVMSG %s :Error printed to console\n" % (channel))
        if errorCode:
            exec(errorCode)
    
def Interrupt():
    SocketSend(irc, "QUIT :Keyboard Interrupt\n")
    irc.close()
    quit()

def main():
    socketQueue = b""
    while True:
        try:
            lines = b""
            ready = select.select([irc], [], [], 1.0)
            if ready[0]:
                lines = irc.recv(2040)
        except Exception: #socket.error, e:   or   socket.timeout, e:
            PrintError()
            return
        else:
            lines = socketQueue + lines # add on any queue from the last recv
            linesSplit = lines.splitlines()
            socketQueue = b""
            if lines and lines[-1] != ord("\n"):
                socketQueue = linesSplit.pop()
            for line in linesSplit:
                try:
                    line = line.decode("utf-8", errors="replace")
                    Print("<-- "+line+"\n")
                    text = line.split()

                    if len(text) > 0:
                        #Reply to server pings
                        if text[0] == "PING":
                            SocketSend(irc, "PONG %s\n" % (text[1]))
                        elif text[0] == "ERROR":
                            irc.close()
                            return #try to reconnect

                    if len(text) > 1:
                        #Only join channel once identified
                        if text[1] == "396":
                            for i in channels:
                                SocketSend(irc, "JOIN %s\n" % (i))
                        #Nickname already in use
                        elif text[1] == "433":
                            SocketSend(irc, "NICK %s-\n" % (text[3]))
                            if NickServ:
                                SocketSend(irc, "ns identify %s %s\n" % (botAccount, botPassword))
                                SocketSend(irc, "ns ghost %s\n" % (botNick))
                                SocketSend(irc, "NICK %s\n" % (botNick))
                        elif text[1] == "437":
                            SocketSend(irc, "NICK %s-\n" % text[3])
                            if NickServ:
                                SocketSend(irc, "ns identify %s %s\n" % (botAccount, botPassword))
                                SocketSend(irc, "ns release %s\n" % (botNick))
                                SocketSend(irc, "NICK %s\n" % (botNick))

                    if len(text) > 2:
                        #Get channel to reply to
                        if text[1] == "PRIVMSG":
                            reply = text[2]
                            if reply == botNick:
                                reply = text[0].split("!")[0].lstrip(":")
                        elif text[1] == "NICK" and text[0].split("!")[0][1:] == botNick:
                            SocketSend(irc, "NICK %s\n" % (botNick))

                    if len(text) >= 4:
                        #Parse line in stocks.py
                        if len(text):
                            Parse(text)

                    if len(text) >= 5:
                        if text[1] == "MODE" and text[2] == "##powder-bots" and text[3] == "+o" and text[4] == botNick:
                            SocketSend(irc, "MODE ##powder-bots -o %s\n" % (botNick))

                    #allow modules to do their own text parsing if needed, outside of raw commands
                    for mod in mods:
                         if hasattr(mods[mod], "Parse"):
                            mods[mod].Parse(line, text)
                except SystemExit:
                    SocketSend(irc, "QUIT :i'm a potato\n")
                    irc.close()
                    quit()
                except Exception:
                    PrintError(channels[0])
        try:
            #allow modules to have a "tick" function constantly run, for any updates they need
            for mod in mods:
                if hasattr(mods[mod], "AlwaysRun"):
                    mods[mod].AlwaysRun(channels[0])
            #TODO: maybe proper rate limiting, but this works for now
            for i in messageQueue:
                Print("--> %s" % i)
                SocketSend(irc, i)
            messageQueue[:] = []
        except Exception:
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
            if command == "%sreload" % (commandChar):
                if len(text) <= 4:
                    SendNotice(username, "No module given")
                    return
                mod = text[4]
                if not os.path.isfile(os.path.join("mods", mod+".py")):
                    return
                commands[mod] = []
                if mod == "stocks":
                    if "stocks" in mods:
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
            elif command == "%seval" % (commandChar):
                try:
                    ret = str(eval(" ".join(text[4:])))
                except Exception as e:
                    ret = str(type(e))+":"+str(e)
                SendMessage(channel, ret)
                return
            elif command == "%sexec" % (commandChar):
                try:
                    exec(" ".join(text[4:]))
                except Exception as e:
                    SendMessage(channel, str(type(e))+":"+str(e))
                return
            elif command == "%squit" % (commandChar):
                quit()

        #actual commands here
        for mod in commands:
            for i in commands[mod]:
                if command == "%s%s" % (commandChar, i[0]):
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
        Print("Keyboard inturrupt, bot shut down")
        break
    except Exception:
        PrintError()
        Print("A strange error occured, reconnecting in 10 seconds")
        sleep(10)
        pass
