import re
from common import *
RegisterMod(__name__)

def GetHealth(account):
    page = GetPage("http://tptapi.com/money.php", account["cookies"]) #temporary until stats.php is done
    hp = re.search("glyphicon-heart'></i> (.+?)</font>", page).group(1)
    account["health"] = (hp.split("/")[0], hp.split("/")[1])
    
def GetInventory(account):
    page = GetPage("http://tptapi.com/inventory.php", account["cookies"])
    items = []
    items.extend(re.findall("<td width='\d+%'>(.*?)</td>", page))
    items[0:4] = []

    account["inventory"] = []
    for i in range(0, len(items), 4):
        itemID = re.search("item=(.+)'", items[i+2]).group(1)
        account["inventory"].append((items[i], items[i+1], itemID))
    return account["inventory"]

def GetItemList(account):
    page = GetPage("http://tptapi.com/store.php", account["cookies"])
    items = []
    items.extend(re.findall("<td width='\d+%'>(.*?)</td>", page))
    items[0:6] = []

    itemList = []
    for i in range(0, len(items), 6):
        itemID = re.search("item=(.+)'", items[i+3]).group(1)
        itemList.append((items[i], items[i+2], itemID, items[i+1]))
    return itemList

def FindItem(account, itemList, itemID):
    found = None
    for i in itemList:
        if i[2] == itemID or i[0][:len(itemID)].lower() == itemID.lower():
            if found and found[1] != i[0]:
                return None
            found = (i[2], i[0])
    if not found:
        return None
    return found

def ItemAction(account, action, itemID):
    return GetPage("http://tptapi.com/item_action.php?opt=%s&item=%s" % (action, itemID), account["cookies"], removeTags = True)

def PrintLocation(account, channel):
    page = GetPage("http://tptapi.com/TPTRPG/index.php", account["cookies"], removeTags = True)
    location = re.search("Your current location: (.+?)&", page, re.DOTALL).group(1).strip().splitlines()
    SendMessage(channel, "Current Location: %s" % location[0])
    print(location)
    for i in location[1:]:
        SendMessage(channel, i.strip())

@command("inventory", needsAccount = True)
def Inventory(username, hostmask, channel, text, account):
    """inventory (no args). Prints which items you own in the store"""
    GetInventory(account)
    if len(account["inventory"]) == 0:
        SendMessage(channel, "Inventory empty")
        return
    SendMessage(channel, ", ".join("07%s: $%s (%s)" % (i[0], i[1], i[2]) for i in account["inventory"]))

@command("itemlist")
def ItemList(username, hostmask, channel, text, account):
    """itemlist (no args). Prints the list of items you can buy in the store"""
    account = GetAccount(ownerHostmask)
    if not account:
        return

    itemList = GetItemList(account)
    SendMessage(channel, ", ".join("07%s: $%s (%s, %s in existence)" % (i[0], i[1], i[2], i[3]) for i in itemList))

@command("itembuy", minArgs = 1, needsAccount = True)
def ItemBuy(username, hostmask, channel, text, account):
    """itembuy <item>. Buys item in the store. It will match and buy partial item names"""
    item = FindItem(account, GetItemList(account), " ".join(text))
    if not item:
        SendMessage(channel, "No such item Name/ID: %s" % " ".join(text))
        return
    
    ItemAction(account, "0", item[0])
    SendMessage(channel, "Bought %s (%s)" % (item[1], item[0]))

@command("itemsell", minArgs = 1, needsAccount = True)
def ItemSell(username, hostmask, channel, text, account):
    """itemsell <item>. Sells the first matching item from your inventory. It will match partial item names"""
    item = FindItem(account, GetInventory(account), " ".join(text))
    if not item:
        SendMessage(channel, "No such item Name/ID: %s" % " ".join(text))
        return
    
    ItemAction(account, "1", item[0])
    SendMessage(channel, "Sold %s (%s)" % (item[1], item[0]))

@command("use", minArgs = 1, needsAccount = True)
def Use(username, hostmask, channel, text, account):
    """use <item>. Uses the first matching item from your inventory to recover hp. It will match partial item names"""
    item = FindItem(account, GetInventory(account), " ".join(text))
    if not item:
        SendMessage(channel, "No such item Name/ID: %s" % " ".join(text))
        return
    
    print(ItemAction(account, "2", item[0]))
    SendMessage(channel, "Used %s (%s)" % (item[1], item[0]))
    
@command("health", needsAccount = True)
def Health(username, hostmask, channel, text, account):
    """health (no args). Prints your current health"""
    GetHealth(account)
    SendMessage(channel, "Current: %s Max: %s" % (account["health"][0], account["health"][1]))

@command("location", needsAccount = True)
def Location(username, hostmask, channel, text, account):
    """location (no args). Prints your current location"""
    PrintLocation(account, channel)

@command("move", minArgs = 1, needsAccount = True)
def Move(username, hostmask, channel, text, account):
    """move N/E/S/W. Moves your character in the RPG game"""
    direction = text[0]
    if direction not in ["N", "E", "S", "W"]:
        SendMessage(channel, "Invalid direction")
        return
    page = GetPage("http://tptapi.com/TPTRPG/RPG_Action.php?Act=Walk&Direction=%s" % direction, account["cookies"], removeTags = True)
    if len(page):
        SendMessage(channel, page)
        return
    PrintLocation(account, channel)

@command("claim", needsAccount = True)
def Claim(username, hostmask, channel, text, account):
    """claim (no args). Claims the spot you are standing on in the rpg game"""
    page = GetPage("http://tptapi.com/TPTRPG/RPG_Action.php?Act=Claim", account["cookies"], removeTags = True)
    if len(page):
        SendMessage(channel, page)
    else:
        SendMessage(channel, "claimed!")
