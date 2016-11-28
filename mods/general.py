import math
import string
from datetime import datetime

from common import *
RegisterMod(__name__)

def AlwaysRun(channel):
	now = datetime.now()
	if now.minute%6 == 1 and now.second == 4:
		Send("PING checkalive\n")

@command("help", minArgs = 1)
def HelpCmd(message):
	"""<command> Shows help for a command."""
	helpCmd = message.GetArg(0)
	for mod in commands:
		for i in commands[mod]:
			if i[0] == helpCmd:
				if i[1].__doc__:
					message.Reply("%s: %s" % (helpCmd, i[1].__doc__))
				else:
					message.Reply("No help text available for %s." % (helpCmd))
				return
	message.ReplyNotice("No such command")

@command("list")
def ListCmd(message):
	"""(no args). Lists all commands."""
	listMod = message.GetArg(0)
	if listMod:
		if not listMod in commands:
			message.ReplyNotice("No such module")
		else:
			message.Reply("Commands: "+", ".join(i[0] for i in commands[listMod]))
	else:
		message.Reply("Modules: "+", ".join(i for i in commands))

@command("commands")
def CommandsCmd(message):
	"""(no args). Lists all commands."""
	cmdlist = []
	for mod in commands:
		cmdlist += commands[mod]
	message.Reply(", ".join(i[0] for i in cmdlist))

@command("ping")
def PingCmd(message):
	"""PONG"""
	if message.commandLine:
		message.Reply("pong %s" % message.commandLine)
	else:
		message.Reply("pong")

@command("join", minArgs = 1, owner = True)
def JoinCmd(message):
	"""(no args). Make the bot join a channel (owner only)."""
	Send("JOIN %s\n" % message.GetArg(0))

@command("part", minArgs = 1, owner = True)
def PartCmd(message):
	"""(no args). Make the bot part a channel (owner only)."""
	Send("PART %s\n" % message.GetArg(0))

#def Parse(raw, text):
#	if text[1] == "324":
#		SendMessage(config.channels[2], "Channel exists: "+text[3] + "; " + text[4])
#	elif text[1] == "403":
#		SendMessage(config.channels[2], "No such channel: "+text[3])

@command("msg", minArgs = 2, owner = True)
def MsgCmd(message):
	"""(msg <channel> <message>). Sends a message to a channel."""
	SendMessage(message.GetArg(0), " ".join(message.GetArg(1, endLine=True)))

@command("raw", minArgs = 1, owner = True)
def RawCmd(message):
	"""(raw <message>). Sends a raw IRC message."""
	Send(message.commandLine + "\n")

"""
@command("check", minArgs = 1)
def CheckCmd(username, hostmask, channel, text):
	""secret command.""
	for i in text:
		Send("MODE ######%s\n" % i)

@command("octal", minArgs = 1)
def OctalCmd(username, hostmask, channel, text):
	""secret command 2.""
	for i in text:
		str = ""
		for char in i.replace("_", " "):
			str = str + "-{0:03o}".format(ord(char))
		Send("MODE ######%s\n" % str.strip("-"))
		#Send("MODE ######%s\n" % str.replace("-", ""))

@command("bruteforce", minArgs = 1, owner=True)
def BruteforceCmd(username, hostmask, channel, text):
	""secret command 3.""
	str = text[0]
	for i in range(26):
		Send("MODE ######%s\n" % str.replace("?", chr(i+65)))
	SendMessage(channel, "Modes sent")

@command("vigenere", minArgs = 2)
def Viginerecmd(username, hostmask, channel, text):
	""(<string> <listofkeys>...). moo""
	for i in text[1:]:
		(enc, dec) = Viginere(text[0], i)
		SendMessage(channel, "Encrypted: %s, Decrypted: %s" % (enc, dec))"""

"""@command("vigenere2", minArgs = 2)
def Viginere2cmd(username, hostmask, channel, text):
	""(<string> <listofkeys>...). moo""
	checked = []
	for i in text[1:]:
		(enc, dec) = Viginere(text[0], i)
		checked.append(dec)
		Send("MODE ####%s\n" % dec)
	SendMessage(config.channels[2], "Checking: " + ", ".join(checked))

@command("vigenere3", minArgs = 2)
def Viginere3cmd(username, hostmask, channel, text):
	""(<keys> <listofstrings>...). moo""
	checked = []
	for i in text[1:]:
		(enc, dec) = Viginere(i, text[0])
		checked.append(dec)
		Send("MODE ####%s\n" % dec)
	SendMessage(config.channels[2], "Checking: " + ", ".join(checked))
	
alpha = string.lowercase
def Viginere(incoming, KEY, offset = 1):
	## subtract 1 so it works with python's 0's index for lists
	## this part actually broke it, and ended up making it a ROT12
	## when it should have been a ROT13
	offset -= 1

	## generate the Vigenere square shading
	chart = dict()
	k = 0
	for letter in alpha:
		if k + offset >= len(alpha):
			## rotation won't go beyond end of row
			sanit = k + offset - len(alpha)
			chart[letter] = alpha[sanit:] + alpha[:sanit]
		else:
			## rotation goes beyond the end of the row
			chart[letter] = alpha[k + offset:] + alpha[:k + offset]
		k += 1

	## display the chart to stdout
	ordered_rows = chart.keys()
	ordered_rows.sort()
	#for x in ordered_rows:
	#	print x, chart[x]
	#print ''

	## pad the key with the length of the incoming text
	multi = math.ceil(len(incoming) / float(len(KEY)))
	long_key = KEY * int(multi)


	## encrypted the incoming text
	j = 0
	output_encrypted = str()
	for x in incoming:
		y = x.lower()
		if y in chart:
			row = chart[y]
			idx = (string.lowercase).find(long_key[j].lower())
			output_encrypted += chart[y][idx]
			j += 1
		else:
			output_encrypted += y

	## decrypt the incoming text
	p = 0
	output_decrypted = str()
	for x in incoming:
		y = x.lower()
		stop = False
		before = len(output_decrypted)
		for letter in chart:
			row = chart[letter]
			if not stop and y in chart:
				idx = (string.lowercase).find(long_key[p].lower())
				if row[idx] == y:
					output_decrypted += letter
					p += 1
					stop = True
		after = len(output_decrypted)
		if before == after:
			output_decrypted += y

		return (output_encrypted.upper(), output_decrypted.upper())
	#SendMessage(config.channels[2], "Encrypted: %s, Decrypted: %s" % (output_encrypted.upper(), output_decrypted.upper()))
	#print 'Encrypted:', output_encrypted.upper()
	#print 'Decrypted:', output_decrypted.upper()"""
