import urllib, urllib2
from cookielib import CookieJar
import socket
import re
from datetime import datetime
from time import sleep

from common import *
RegisterMod(__name__)

output = 0
def AlwaysRun(channel):
    global output
    global watched
    global history
    now = datetime.now()
    if now.minute % 10 == 0 and now.second ==  15:
        #return
        if now.hour%2 == 0 and now.minute == 10:
        #if now.minute == 0:
            history = {}
        GetStockInfo(True)
        if len(watched) or output:
            PrintStocks(channel, False, output != 1)
            PrintNews(channel, True)
        watched = []
        sleep(1)

def Login(channel, hostmask, username, password):
    for i in logins.values():
        if i["username"] == username:
            SendMessage(channel, "Someone else is already logged in as %s" % username)
            return False
    
    req = urllib2.Request("http://tptapi.com/login_proc.php?login", urllib.urlencode({"Username":username, "Password":password}))
    response = urllib2.urlopen(req)
    if response.read().find("login.php?error=1") > 0:
        SendMessage(channel, "Invalid password for %s" % username)
        return False
    cj = CookieJar()
    cj.extract_cookies(response, req)

    logins[hostmask] = {}
    logins[hostmask]["cookies"] = {}
    logins[hostmask]["portfolio"] = {}
    logins[hostmask]["username"] = username
    #logins[hostmask]["opener"] = opener

    tempcookies = []
    for i in list(cj):
        if i.name in ["T_UID", "T_UIK", "T_UIS"]:
            tempcookies.append("%s=%s" % (i.name, i.value))
    logins[hostmask]["cookies"] = "; ".join(tempcookies)
    SendMessage(channel, "Successfully logged in")
    return True

results = {}
history = {}
def GetStockInfo(new = False):
    page = GetPage("http://tptapi.com/getjson.php?type=stock")
    stocks = []
    stocks.extend(re.findall("\"([^\"]*)\"", page))
    for i in range(0,len(stocks), 4):
        results[stocks[i]] = {'value':stocks[i+2]}
        if (new):
            if not stocks[i] in history:
                history[stocks[i]] = []
            history[stocks[i]].append(int(stocks[i+2]))

def GetPortfolioInfo(account, element = None):
    page = GetPage("http://tptapi.com/portfolio.php", account["cookies"])
    stocks = []
    for i in page.splitlines():
        stocks.extend(re.findall("<td width='\d+%'>([^<>]*)</td>", i))
    
    output = ""
    for i in range(0, len(stocks), 4):
        try:
            if stocks[i] == "":
                continue
            output = output + "07%s (%s): %s  " % (stocks[i], stocks[i+2], stocks[i+1])
            if element == stocks[i]:
                return int(stocks[i+1])
        except:
            pass
    if element:
        return None
    return output

def GetMoney(account):
    page = GetPage("http://tptapi.com/money.php", account["cookies"])
    start = page.find("Current Balance:")+21
    return int(re.sub(",", "", page[start:start+page[start:].find(".")]))

#You cannot sell more stock than how much you own!
#INVALID Field!
def BuySellStocks(account, action, element, amount, stockClass = "1"):
    return GetPage("http://tptapi.com/stockProc.php?opt=%s&stock=%s" % (action, element), account["cookies"], {"shares":amount,"class":stockClass}, True).replace("\n", " ")

def GetChange(old, new):
    #dividing by 0 is bad
    if old == 0:
        return "040%"
    if old < new:
        color = "09"
    elif old > new:
        color = "04"
    else:
        color = "08"
    return color + str(int((float(new)-old)/old*1000)/10.0) + "%"

watched = []
def PrintStocks(channel, allPercentages = False, onlyOwned = False):
    output = ""
    stocks = results.keys()
    if onlyOwned:
        stocks = [i for i in watched]
        for i in logins.values():
            for j in i["portfolio"]:
                if i["username"] == "jacob2" and i["portfolio"][j]["shares"] > 0 and j not in stocks:
                    stocks.append(j)
    if not len(stocks):
        return
    for i in sorted(stocks):
        if i in watched:
            output = output + "03"
        else:
            output = output + "07"
        if i in results:
            output = output + i + " - $" + results[i]["value"]
        if (i in watched or allPercentages or onlyOwned) and i in history and len(history[i]) > 1:
            output += " " + GetChange(history[i][-2], history[i][-1])
        output += "  "
        #overflow, separate into multiple messages
        if len(output) > 400:
            SendMessage(channel, output)
            output = ""
    SendMessage(channel, output)

def PrintMniipRatings(channel):
    page = GetPage("http://mniip.com/powder/stock/best.js")
    ratings = page.split('"')
    ratings[0] = ratings[0][5:]
    output = "PowJones Stock Ratings: "
    for i in range(0, len(ratings)-1, 2):
        output = output + "07" + ratings[i].strip("{,:\n") + ": " + ratings[i+1] + " "
    SendMessage(channel, output)

def PrintRatings(channel, element = None, all = False):
    output = "PowJones Stock Ratings: "
    for i in sorted(results):
        if ((not element and int(results[i]["value"]) >= 5) or i == element) and i not in ignoredStocks and i in history and len(history[i]) > 1:
            """minn = history[i][0]
            maxx = history[i][1]
            for j in history[i]:
                if j < minn:
                    minn = j
                if j > maxx:
                    maxx = j
            #average = (maxx+minn)/2"""

            asdf = 1.25#1+len(history[i])*.05
            #if len(history[i]) > 5:
            average = sum(history[i])/len(history[i])
            rating = GetChange(int(results[i]["value"]), average)
            if average/asdf > int(results[i]["value"]) or element or all:
                output = output + "07" + i + ": " + rating + " "
            """else:
                average = sum(history[i])/len(history[i])
                rating = GetChange(int(results[i]["value"]), average)
                if average > int(results[i]["value"]) or element:
                    output = output + "07" + i + ": " + rating + " """
            
            """rating = (float(results[i]["value"])-minn)/(maxx-minn)
            #rating = GetChange(1, rating)
            #output = output + "07" + i + ": " + rating + " "
            if rating < .4:
                output = output + "07" + i + ": 09" + str(int((1-rating)*100)) + "% " """

            if len(output) > 400:
                SendMessage(channel, output)
                output = ""
    SendMessage(channel, output)
                    
    
def PrintStockValue(channel, stock):
    change = ""
    if stock in history and len(history[stock]) > 1:
        change = GetChange(history[stock][-2], history[stock][-1])
    if stock in results:
        SendMessage(channel, "%s %s" % (results[stock]["value"], change))

def PrintHistory(channel, stock):
    output = "07" + stock + ": "
    if stock in history:
        for i in history[stock]:
            output = output + str(i) + ", "
        SendMessage(channel, output[:-2])

goodNews = ["grant", "stealing their newest", "purchases 50 uni", "new employees", "economy is looking great", "expected to be up"]
badNews = ["employees WILL be cut", "employee cutbacks", "expected to be down", "downgraded", "recall for their", "class action lawsuit", "center of market iussues", "sales may be slowing", "Powder Game"]
terribleNews = ["bankruptcy", "liquidation", "shutters"]
def NewsColor(news):
    for i in goodNews:
        if i in news:
            return "09"
    for i in badNews:
        if i in news:
            return "04"
    for i in terribleNews:
        if i in news:
            return "04,01"
    return "08"

def FormatNews(newsitem):
    return "%s%s (%s) %s 07(%s, 07%s)" % (NewsColor(newsitem[3]), newsitem[2], newsitem[1], newsitem[3], newsitem[4], newsitem[0])

def IsInNews(news, newsID):
    for i in news:
        if i[0] == newsID:
            return True
    for i in specialNews:
        if i[0] == newsID:
            return True
    return False

news = []
specialNews = []
ignoredStocks = []
def PrintNews(channel, first = False, special = False, stock = None):
    page = GetPage("http://tptapi.com/getjson.php?type=news")
    tempnews = re.findall("\"([^\"]*)\"", page)

    for i in range(0, len(tempnews), 6):
        if not IsInNews(news, tempnews[i+1]):
            newsItem = tempnews[i+3]
            if "FEC DISCLOSURE" in newsItem:
                specialNews.append((tempnews[i+1], "<company name>", newsItem.split()[0], " ".join(newsItem.split()[2:]), tempnews[i+5]))
                SendMessage(channel, FormatNews(specialNews[-1]))
            elif "issued dividends" in newsItem:
                specialNews.append((tempnews[i+1], "<compay name>", newsItem.split()[0], " ".join(newsItem.split()[1:]), tempnews[i+5]))
                SendMessage(channel, FormatNews(specialNews[-1]))
            elif NewsColor(newsItem) == "04,01":
                newsName = newsItem.split("(")[0].strip()
                newsItem = " ".join(newsItem.split("(")[1:])
                specialNews.append((tempnews[i+1], newsName, newsItem.split()[0].strip(")"), " ".join(newsItem.split()[1:]), tempnews[i+5]))
                SendMessage(channel, FormatNews(specialNews[-1]))
                if newsItem.split()[0].strip(")") not in ignoredStocks:
                    ignoredStocks.append(newsItem.split()[0].strip(")"))
            else:
                newsName = newsItem.split("(")[0].strip()
                newsItem = " ".join(newsItem.split("(")[1:])
                news.append((tempnews[i+1], newsName, newsItem.split()[0].strip(")"), " ".join(newsItem.split()[1:]), tempnews[i+5]))

    newslist = specialNews if special else news
    if stock:
        for i in newslist[::-1]:
            if i[2] == stock:
                SendMessage(channel, FormatNews(i))
                if first:
                    return
    else:
        for i in newslist[-1:-6:-1]:
            SendMessage(channel, FormatNews(i))
            if first:
                return

""":wolfe.freenode.net 332 logbot614 ###stocks :Illegal insider trading takes place
 here, also drug smuggling

http://pastebin.com/CvwxHKUc - Javert
http://pastebin.com/5CYuBbtx - cracker64"""

@command("print")
def PrintCmd(username, hostmask, channel, text, account):
    """(print [owned]). Print all current stock prices. Add 'owned' to only print stocks which are owned by someone."""
    GetStockInfo()
    PrintStocks(channel, False, True if len(text) > 0 and text[0] == "owned" else False)

@command("printall")
def PrintAllCmd(username, hostmask, channel, text, account):
    """(printall [owned]). Print all current stock prices and percent changes.  Add 'owned' to only print stocks which are owned by someone."""
    GetStockInfo()
    PrintStocks(channel, True, True if len(text) > 0 and text[0] == "owned" else False)

@command("print2", owner = True)
def Print2Cmd(username, hostmask, channel, text, account):
    """(no args). Updates stock history with the current prices (owner only)."""
    GetStockInfo(True)

@command("login", minArgs = 2)
def LoginCmd(username, hostmask, channel, text, account):
    """(login <tptusername> <tptpassword>). Logs you in so you can buy stocks. All passwords are safely stored on jacob1's computer for future use"""
    if hostmask in logins:
        SendMessage(channel, "You are already logged in as %s" % logins[hostmask]["username"])
        return
    if Login(channel, hostmask, text[0], text[1]):
        SendMessage("#TPTAPIStocks", "Logged in: %s!%s" % (username, hostmask))

@command("logout", needsAccount = True)
def LogoutCmd(username, hostmask, channel, text, account):
    """logs you out and deletes all session info"""
    if hostmask in logins:
        SendMessage(channel, "Logged out: %s" % logins[hostmask]["username"])
        del logins[hostmask]

@command("stock", minArgs = 1)
def StockCmd(username, hostmask, channel, text, account):
    """(stock <stockname>). Prints current stock price and percent change"""
    GetStockInfo()
    PrintStockValue(channel, text[0].upper())

@command("history", minArgs = 1)
def HistoryCmd(username, hostmask, channel, text, account):
    """(history <stockname>). Gives a history of all previous stock prices since the last price range change"""
    PrintHistory(channel, text[0].upper())

@command("buy", minArgs = 2, needsAccount = True)
def BuyCmd(username, hostmask, channel, text, account):
    """(buy <stockname> <numberofstocks> [a]) or (buy <stockname> <percent>% [a]). Has two options, can either buy a specific number of stocks, or spend a certain percentage of your money on the stock. Buys class B stock by default"""
    element = text[0].upper()
    total = text[1]
    stockClass = "1"
    if len(text) > 2 and text[2].lower() == "a":
        stockClass = "0"

    if element not in history:
        SendMessage(channel, "%s is not a valid stock name" % element)
        return
    if total[-1] == "%":
        GetStockInfo()
        if element in results and int(results[element]["value"]) == 0:
            SendMessage(channel, "Error: %s is bankrupt!" % element)
            return
        money = GetMoney(account)
        total = int(money/int(results[element]["value"])*float(total[:-1])/100)
        SendMessage(channel, "Buying %s shares of %s" % (str(total), element))
    try:
        total = int(total)
    except:
        SendMessage(channel, "%s is not a valid number" % total)
        return

    SendMessage(channel, BuySellStocks(account, 1, element, total, stockClass))
    if element in account["portfolio"]:
        account["portfolio"][element]["shares"] = int(account["portfolio"][element]["shares"]) + int(total)
    else:
        account["portfolio"][element] = {'shares':total}
    if element not in watched and account["username"] == "jacob2":
        watched.append(element)
    #SendMessage("Crackbot", "./stock watch %s" % element)

@command("sell", minArgs = 2, needsAccount = True)
def SellCmd(username, hostmask, channel, text, account):
    """(sell <stockname> <numberofstocks> [a]). Sells a specific amount of stocks. Buys class B stock by default"""
    element = text[0].upper()
    stockClass = "1"
    if len(text) > 2 and text[2].lower() == "a":
        stockClass = "0"

    try:
        amount = int(text[1])
    except:
        SendMessage(channel, "%s is not a valid number" % text[1])
        return
    if element not in history:
        SendMessage(channel, "%s is not a valid stock name" % element)
        return
    SendMessage(channel, BuySellStocks(account, 0, element, amount, stockClass))
    
    if element in account["portfolio"]:
        account["portfolio"][element]["shares"] -= amount

@command("sellall", minArgs = 1, needsAccount = True)
def SellAllCmd(username, hostmask, channel, text, account):
    """(sellall <stockname> [a]). Seels all stocks you bought using the bot. If you didn't buy it with the bot, it won't work. Buys class B stock by default"""
    element = text[0].upper()
    stockClass = "1"
    if len(text) > 1 and text[1].lower() == "a":
        stockClass = "0"

    if element not in account["portfolio"]:
        stocks = GetPortfolioInfo(account, element)
        if not stocks:
            SendMessage(channel, "You do not own any shares of %s" % element)
            return
    else:
        stocks = int(account["portfolio"][element]["shares"])
    if stocks > 100000000000000:
        SendMessage(channel, BuySellStocks(account, 0, element, int(stocks*.9999999999), stockClass))
        leftover = GetPortfolioInfo(account, element)
        if leftover:
            #SendMessage(channel, "Selling leftover %s" % str(leftover))
            SendMessage(channel, BuySellStocks(account, 0, element, leftover, stockClass))

    else:
        #print account["portfolio"][element]["shares"]
        SendMessage(channel, BuySellStocks(account, 0, element, stocks, stockClass))
    if element in account["portfolio"]:
        account["portfolio"][element]["shares"] = 0

@command("money", needsAccount = True)
def MoneyCmd(username, hostmask, channel, text, account):
    """(no args). Prints the exact amount of money you own with no commas, if logged in"""
    SendMessage(channel, str(GetMoney(account)))

@command("give", minArgs = 2, needsAccount = True)
def GiveCmd(username, hostmask, channel, text, account):
    """(give <username> <amount>). Gives money to another user."""
    SendMessage(channel, GetPage("http://tptapi.com/sendProc.php", account["cookies"], {"reciever":text[0], "amount":text[1]}, True))

@command("portfolio", needsAccount = True)
def PortfolioCmd(username, hostmask, channel, text, account):
    """(no args). Prints everything in your portfolio, if logged in"""
    info = GetPortfolioInfo(account)
    if not info:
        SendMessage(channel, "Portfolio empty")
    else:
        SendMessage(channel, info)

@command("rate")
def RateCmd(username, hostmask, channel, text, account):
    """(rate [<stockname>]/[all]). If no arguments, only lists the ratings for the best stocks."""
    now = datetime.now()
    if now.hour%2 == 0 and now.minute < 10:
        SendMessage(channel, "Ratings will not be available until the 10 minute mark")
        return
    GetStockInfo()
    if len(text) and text[0] == "all":
        PrintRatings(channel, None, True)
    else:
        PrintRatings(channel, text[0].upper() if len(text) else None)

@command("mrate")
def MrateCmd(username, hostmask, channel, text, account):
    """(no args). Fetches alternative ratings from http://mniip.com/powder/stock/"""
    PrintMniipRatings(channel)

@command("watch", minArgs = 1)
def WatchCmd(username, hostmask, channel, text, account):
    """(watch <stockname>). Watches a stock, when the prices change every 10 minutes it will tell you if it went up or down"""
    element = text[0].upper()
    if element in history:
        if element not in watched:
            watched.append(element)
        SendMessage(channel, "Now watching %s" % element)
    else:
        SendMessage(channel, "%s is not a valid stock name" % element)

@command("news")
def NewsCmd(username, hostmask, channel, text, account):
    """(news [<stockname>]/[latest]/[special]). Prints the current news. Don't abuse this. 'latest' only returns the most recent news item and 'special' uses the special news list."""
    latest = False
    special = False
    if len(text) > 0:
        latest = "latest" in text
        special = "special" in text
    stock = text[-1].upper() if len(text) > 0 and text[-1] not in ["latest", "special"] else None
    PrintNews(channel, latest, special, stock)

@command("output")
def OutputCmd(username, hostmask, channel, text, account):
    """(no args). Toggle printing stock output every 10 minutes."""
    global output
    output = (output + 1) % 3
    SendMessage(channel, "Output has been turned %s" % ("on" if output else "off"))

