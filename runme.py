import stocks
import socket
import select
import traceback
from time import sleep
import atexit

server = "irc.freenode.net"
channel = "#TPTAPIStocks"
botNick = "stockbot614"
botIdent = "stockbot"
botRealname = "TPTAPI stock helper bot"
connected = False

def GetIRCpassword():
    with open("passwords.txt") as f:
        return f.readlines()[0].strip()

def Connect():
    global irc
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.connect((server,6667))
    irc.setblocking(0)
    irc.send("USER %s %s %s :%s\n" % (botIdent, botNick, botNick, botRealname))
    irc.send("NICK %s\n" % botNick)
    irc.send("PRIVMSG NickServ :identify jacobot %s\n" % GetIRCpassword())
    stocks.SetIRC(irc)
    sleep(7)

def ReadPrefs():
    with open('logins.txt') as f:
        stocks.logins = {}
        for line in f:
            if len(line.strip()):
                cookies = line.split("|")
                stocks.logins[cookies[0]] = {"username":cookies[1], "portfolio":{}, "cookies":cookies[2].strip()}

def WritePrefs():
    with open('logins.txt', 'w') as f:
        for i in stocks.logins:
            f.write("%s|%s|%s\r\n" % (i, stocks.logins[i]["username"], stocks.logins[i]["cookies"]))
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
    global channel
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
        except socket.error, e:
            PrintError()
            quit()
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
                    if len(text) >= 4 and stocks.CheckOwner(text[0]) and text[1] == "PRIVMSG" and text[2][0] == "#":
                        command = text[3].lower().lstrip(":")
                        if command == "!!reload":
                            logins = stocks.logins
                            history = stocks.history
                            watched = stocks.watched
                            news = stocks.news
                            reload(stocks)
                            stocks.logins = logins
                            stocks.history = history
                            stocks.watched = watched
                            stocks.news = news
                            irc.send("PRIVMSG %s :Reloaded stocks.py\n" % reply)
                    #Parse line in stocks.py
                    if len(text):
                        stocks.Parse(text)
                except KeyboardInterrupt:
                    Interrupt()
                except:
                    PrintError(reply)
        try:
            stocks.AlwaysRun(channel)
        except KeyboardInterrupt:
            Interrupt()
        except:
            PrintError(channel)

Connect()
stocks.GetStockInfo(True)
ReadPrefs()
main()
