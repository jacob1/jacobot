import socket
import select
import traceback
from time import sleep
import atexit
import os.path

if not os.path.isfile("config.py"):
    import shutil
    shutil.copyfile("config.py.default", "config.py")
    print("config.py.default copied to config.py")
execfile("config.py")
if not configured:
    print("you have not configured the bot, open up config.py to edit settings")
    quit()

from common import *
import stocks

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
        logins = {}
        for line in f:
            if len(line.strip()):
                cookies = line.split("|")
                stocks.logins[cookies[0]] = {"username":cookies[1], "portfolio":{}, "cookies":cookies[2].strip()}

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
        except socket.timeout, e:
            if e.args[0] == "timed out":
                continue
            else:
                PrintError()
                return
        except socket.error, e:
            PrintError()
            return
        except KeyboardInterrupt:
            Interrupt()
        else:
            if len(line):
                if ":!!login" in line:
                    print("<someone logging in>")
                else:
                    print(line)
                text = line.split()
                #Only join channel once identified
                if len(text) > 1 and text[1] == "396":
                    irc.send("JOIN %s\n" % channel)
                
                #Get channel to reply to
                if len(text) > 2 and text[1] == "PRIVMSG":
                    reply = text[2]
                    if reply == botNick:
                        reply = text[0].split("!")[0].lstrip(":")
                #Reply to pings
                elif len(text) > 0 and text[0] == "PING":
                    irc.send("PONG %s\n" % text[1])
                
                try:
                    #Admin commands
                    if len(text) >= 4 and CheckOwner(text[0]) and text[1] == "PRIVMSG" and text[2][0] == "#":
                        command = text[3].lower().lstrip(":")
                        if command == "!!reload":
                            commands[:] = []
                            logins = stocks.logins
                            history = stocks.history
                            watched = stocks.watched
                            news = stocks.news
                            specialNews = stocks.specialNews
                            reload(stocks)
                            stocks.logins = logins
                            stocks.history = history
                            stocks.watched = watched
                            stocks.news = news
                            stocks.specialNews = specialNews
                            irc.send("PRIVMSG %s :Reloaded stocks.py\n" % reply)
                        elif command == "!!eval":
                            try:
                                ret = str(eval(" ".join(text[4:])))
                            except Exception as e:
                                ret = str(type(e))+":"+str(e)
                            irc.send("PRIVMSG %s :%s\n" % (channel, ret))
                    #Parse line in stocks.py
                    if len(text):
                        Parse(text)
                except KeyboardInterrupt:
                    Interrupt()
                except:
                    PrintError(reply)
        try:
            stocks.AlwaysRun(channel)
            #TODO: maybe proper rate limiting, but this works for now
            for i in messageQueue:
                irc.send(i)
            messageQueue[:] = []
        except KeyboardInterrupt:
            Interrupt()
        except:
            PrintError(channel)

def Parse(text):
    if len(text) < 4:
        return
    if text[1] == "PRIVMSG":
        channel = text[2]
        username = text[0].split("!")[0].lstrip(":")
        hostmask = text[0].split("!")[1]
        command = text[3].lower().lstrip(":")
        if channel == "stockbot614":
            channel = username

        for i in commands:
            if command == "!!"+i[0]:
                i[1](username, hostmask, channel, text[4:])

Connect()
stocks.GetStockInfo(True)
ReadPrefs()
while True:
    main()
