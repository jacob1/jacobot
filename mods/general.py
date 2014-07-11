from common import *
RegisterMod(__name__)

@command("help", minArgs = 1)
def HelpCmd(username, hostmask, channel, text, account):
    """<command> Shows help for a command."""
    for mod in commands:
        for i in commands[mod]:
            if i[0] == text[0] and i[1].__doc__:
                SendMessage(channel, "%s: %s" % (text[0], i[1].__doc__))
                return
    SendNotice(username, "No such command")

@command("list")
def ListCmd(username, hostmask, channel, text, account):
    """(no args). Lists all commands."""
    if len(text):
        if not text[0] in commands:
            SendNotice(username, "No such module")
        else:
            SendMessage(channel, "Commands: "+", ".join(i[0] for i in commands[text[0]]))
    else:
        SendMessage(channel, "Modules: "+", ".join(i for i in commands))

@command("commands")
def CommandsCmd(username, hostmask, channel, text, account):
    """(no args). Lists all commands."""
    cmdlist = []
    for mod in commands:
        cmdlist += commands[mod]
    SendMessage(channel, ", ".join(i[0] for i in cmdlist))

@command("ping")
def PingCmd(username, hostmask, channel, text, account):
    """PONG"""
    SendMessage(channel, "pong")

@command("join", minArgs = 1, owner = True)
def JoinCmd(username, hostmask, channel, text, account):
    """(no args). Make the bot join a channel (admin only)."""
    Send("JOIN %s\n" % text[0])

@command("part", minArgs = 1, owner = True)
def PartCmd(username, hostmask, channel, text, account):
    """(no args). Make the bot part a channel (admin only)."""
    Send("PART %s\n" % text[0])
