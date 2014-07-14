import re
from common import *
RegisterMod(__name__)

def GetHealth(account):
    page = GetPage("http://tptapi.com/money.php", account) #temporary until stats.php is done
    hp = re.search("glyphicon-heart'></i> (.+?)</font>", page).group(1)
    account["health"] = (hp.split("/")[0], hp.split("/")[1])
    
def GetInventory(account):
    page = GetPage("http://tptapi.com/inventory.php", account)
    items = []
    items.extend(re.findall("<td width='\d+%'>(.+?)</td>", page))
    items[0:4] = []

    account["inventory"] = []
    for i in range(0, len(items), 4):
        itemID = re.search("item=(.+)'", items[i+2]).group(1)
        account["inventory"].append((items[i], items[i+1], itemID))
    return account["inventory"]

def GetItemList(account):
    page = GetPage("http://tptapi.com/store.php", account)
    items = []
    items.extend(re.findall("<td width='\d+%'>(.+?)</td>", page))
    items[0:4] = []

    itemList = []
    for i in range(0, len(items), 4):
        itemID = re.search("item=(.+)'", items[i+3]).group(1)
        itemList.append((items[i], items[i+2], itemID, items[i+1]))
    return itemList

def FindItem(account, itemList, itemID):
    found = None
    for i in itemList:
        if i[2] == itemID or i[0][:len(itemID)].lower() == itemID.lower():
            if found:
                return (itemID, itemID) # no match
            found = (i[2], i[0])
    if not found:
        return (itemID, itemID) # no match
    return found

def ItemAction(account, action, itemID):
    return GetPage("http://tptapi.com/item_action.php?opt=%s&item=%s" % (action, itemID), account, removeTags = True)
    
@command("inventory", needsAccount = True)
def Inventory(username, hostmask, channel, text, account):
    GetInventory(account)
    if len(account["inventory"]) == 0:
        SendMessage(channel, "Inventory empty")
        return
    SendMessage(channel, ", ".join("07%s: $%s (%s)" % (i[0], i[1], i[2]) for i in account["inventory"]))

@command("itemlist")
def ItemList(username, hostmask, channel, text, account):
    account = GetAccount(ownerHostmask)
    if not account:
        return

    itemList = GetItemList(account)
    SendMessage(channel, ", ".join("07%s: $%s (%s, %s in existence)" % (i[0], i[1], i[2], i[3]) for i in itemList))

@command("itembuy", minArgs = 1, needsAccount = True)
def ItemBuy(username, hostmask, channel, text, account):
    item = FindItem(account, GetItemList(account), " ".join(text))
    if item[0] == item[1]:
        SendMessage(channel, "No such item Name/ID: %s" % item[0])
        return
    
    ItemAction(account, "0", item[0])
    SendMessage(channel, "Bought %s (%s)" % (item[1], item[0]))

@command("itemsell", minArgs = 1, needsAccount = True)
def ItemSell(username, hostmask, channel, text, account):
    item = FindItem(account, GetInventory(account), " ".join(text))
    if item[0] == item[1]:
        SendMessage(channel, "No such item Name/ID: %s" % item[0])
        exec item[0]
        return
    
    ItemAction(account, "1", item[0])
    SendMessage(channel, "Sold %s (%s)" % (item[1], item[0]))

@command("use", minArgs = 1, needsAccount = True)
def Use(username, hostmask, channel, text, account):
    item = FindItem(account, " ".join(text))
    if item[0] == item[1]:
        SendMessage(channel, "No such item Name/ID: %s" % item[0])
        return
    
    print(ItemAction(account, "2", item[0]))
    SendMessage(channel, "Used %s (%s)" % (item[1], item[0]))
    
@command("health", needsAccount = True)
def Health(username, hostmask, channel, text, account):
    GetHealth(account)
    SendMessage(channel, "Current: %s Max: %s" % (account["health"][0], account["health"][1]))
