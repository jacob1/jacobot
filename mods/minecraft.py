import time
import json
import math
import config
import subprocess
import sys
import itertools

try:
	if 'SourceRcon' in sys.modules:
		del sys.modules['SourceRcon']
	import SourceRcon
	has_rcon = True
except ImportError:
	has_rcon = False
	rcon_error = False

from common import *
RegisterMod(__name__)

AddSetting(__name__, "craftinglist-filename", "mods/minecraft-craftinglist.txt")
AddSetting(__name__, "dynmap-url", "http://dynmap.starcatcher.us")
AddSetting(__name__, "rcon-address", "localhost")
AddSetting(__name__, "rcon-port", "25575")
AddSetting(__name__, "rcon-password", "")
LoadSettings(__name__)

if has_rcon:
	try:
		rcon = SourceRcon.SourceRcon(GetSetting(__name__, "rcon-address"), int(GetSetting(__name__, "rcon-port")), GetSetting(__name__, "rcon-password"))
		rcon_error = False
	except SourceRcon.SourceRconError:
		has_rcon = False
		rcon_error = True

def Parse(raw, text):
	minecraftRelayMatch = re.match("^:potatorelay!~?mcrelay@unaffiliated/jacob1/bot/jacobot PRIVMSG #powder-mc :(.*)$", raw)
	if minecraftRelayMatch:
		message = minecraftRelayMatch.group(1)
		messageMatch = re.match("\u000314\[(\S+) connected\]", message)
		if messageMatch:
			username = messageMatch.group(1)
			motd = None
			#motd = "[MOTD] This server will be reset and upgraded to 1.13 this weekend (21st/22nd), a download of the old map will be made available"
			#motd = "[MOTD] The planned reset this weekend (21st/22nd) may be delayed if spigot does not update"
			#motd = "[MOTD] This server has been reset and updated to 1.13. Have fun, and watch out for bugs"
			#motd = "[MOTD] Dynmap is now working again, you can view an online map at dynmap.starcatcher.us"
			#motd = "[MOTD] This server will be updated to 1.13.1 when spigot and bungeecord both update"
			#motd = "[MOTD] Server upgraded to 1.13.1. Dynmap will be re-enabled shortly"
			#motd = "[MOTD] The dynmap database has been migrated to a new server and is currently in the process of re-rendering the entire world"
			#motd = "[MOTD] We will be updating to 1.15 by the weekend, after testing plugins to make sure they don't break. A server reset is not planned"
			#motd = "[MOTD] Server is upgraded to 1.15. Dynmap will be re-added when that plugin is updated to 1.15"
			#motd = "[MOTD] This server will be upgraded to 1.16 and reset the weekend of June 26th/27st. Details: https://tpt.io/.312730"
			#motd = "[MOTD] The map has been reset. Have fun on the new world :)"
			if motd:
				try:
					RunRconCommand(None, 'tellraw {0} {{"text":"{1}", "color":"green"}}'.format(username, motd))
				except:
					pass

class CraftingList(object):
	recipes = {}
	replacements = {}

	def _ParseItem(self, line):
		pieces = line.lower().split('|')
		(item, recipelines, amount) = "", "", 0
		if len(pieces) != 3:
			raise Exception("Could not parse line: {0}".format(line))
		item = pieces[0].strip()
		recipelines = pieces[-1].split('/')
		if len(pieces) == 3:
			amount = int(pieces[1].strip())

		aliases = item.split(",")
		orig = True
		for alias in aliases:
			fixedalias = self._Replace(alias)
			self.recipes[fixedalias] = {"recipe" : [], "amount" : amount, "displayname" : aliases[0], "orig" : orig}
			for something in recipelines:
				self.recipes[fixedalias]["recipe"].append([a.strip() for a in something.split('-')])
			orig = False

	def _ParseReplacement(self, line):
		pieces = line.lower().split('|')
		if len(pieces) != 2:
			raise Exception("Could not parse line: {0}".format(line))
		old = pieces[0].strip()
		new = pieces[1].strip()
		self.replacements[old] = new

	def __init__(self):
		craftinglisttxt = open(GetSetting(__name__, "craftinglist-filename"))
		lines = craftinglisttxt.readlines()
		craftinglisttxt.close()
		for line in lines:
			if len(line) and line[0] == ' ':
				self._ParseItem(line)
			elif len(line) and line[0] == "=":
				self._ParseReplacement(line[1:])
				
	def CalcRecipe(self, name, amount):
		try:
			amount = int(amount)
			if amount <= 0:
				raise ValueError()
		except ValueError:
			return "Amount must be a valid positive integer"
	
		name = self._Replace(name.lower())
		if not name in self.recipes:
			return "Couldn't find recipe, try using {0}search".format(config.commandChar)
		recipe = self.recipes[name]["recipe"]
		r_amount = self.recipes[name]["amount"]
		
		craft_amount = math.ceil(amount / r_amount) # Amount <item> needs to be crafted
		item_amount = {} # Dict of item required : amount
		
		for required_item in itertools.chain.from_iterable(recipe):
			if not required_item.strip():
				continue
			item_amount[required_item] = item_amount.get(required_item, 0) + 1
			
		output = []
		for item in item_amount:
			required_amount = craft_amount * item_amount[item]
			print(item, required_amount)
			if required_amount > 1e9:
				formatted_number = "{:.2e}".format(required_amount)
			elif required_amount >= 1e6:
				formatted_number = "{:0.2f}M".format(required_amount / 1e6)
			elif required_amount >= 1e3:
				formatted_number = "{:0.2f}k".format(required_amount / 1e3)
			else:
				formatted_number = "{}".format(required_amount)
			output.append("{} {}".format(formatted_number, item))
			
		return ", ".join(output)
		

	def PrintRecipe(self, name):
		name = name.lower()
		fixedname = self._Replace(name)
		if not fixedname in self.recipes:
			return "Couldn't find recipe, try using {0}search".format(config.commandChar)
		recipe = self.recipes[fixedname]["recipe"]
		amount = self.recipes[fixedname]["amount"]
		longest = [0, 0, 0]
		for i in range(len(recipe)):
			for j in range(len(recipe[i])):
				if len(recipe[i][j]) > longest[j]:
					longest[j] = len(recipe[i][j])

		output = ""
		for i in range(len(recipe)):
			for j in range(len(recipe[i])):
				length = len(recipe[i][j])

				output += "_"*int((longest[j]+2-length)/2)
				output += recipe[i][j]
				output += "_"*int((longest[j]+3-length)/2)
				if j != len(recipe[i])-1:
					output += "|"
			if amount and i == 0:
				output += " ({0})".format(amount)
			output += "\n"
		return output.strip()

	def _SearchRecipeInner(self, recipe, name, fixedname):
		for i in recipe:
			for j in i:
				if name == j or fixedname == j:
					return name

	def SearchRecipe(self, name):
		exactMatches = []
		closeMatches = []
		badMatches = []
		name = name.lower()
		fixedname = self._Replace(name)
		for recipe, recipedict in self.recipes.items():
			if not recipedict["orig"]:
				continue
			if fixedname == recipe:
				exactMatches.append(recipedict["displayname"])
			elif fixedname in recipe or name in recipe:
				closeMatches.append(recipedict["displayname"])
			else:
				match = self._SearchRecipeInner(recipedict, name, fixedname)
				if match:
					badMatches.append(recipedict["displayname"])
		if len(exactMatches) or len(closeMatches) or len(badMatches):
			return ", ".join(exactMatches+closeMatches+badMatches)
		else:
			return "No matches"

	def _Replace(self, name):
		for old, new in self.replacements.items():
			name = name.replace(old, new)
		return name

recipes = CraftingList()

@command("craft", minArgs = 1, rateLimit=True)
def Craft(message):
	"""(craft <item>). Prints a minecraft crafting recipe"""
	output = recipes.PrintRecipe(message.commandLine)
	for line in output.splitlines():
		message.Reply(line)
		
@command("craftcalc", minArgs = 2, rateLimit=True)
def Craftcalc(message):
	"""(craftcalc <item> <amount>). Lists materials required to craft <amount> of <item>"""
	message.Reply(recipes.CalcRecipe(*message.commandLine.rsplit(" ", 1)))

@command("search", minArgs = 1)
def Search(message):
	"""(search <item>). Searches for minecraft recipes matching or containing an item"""
	searchTerm = message.commandLine
	if len(searchTerm) < 3:
		message.Reply("Search text too short")
		return

	output = recipes.SearchRecipe(searchTerm)
	for line in output.splitlines():
		message.Reply(line)
		

# Location conversion commands

def location_conversion(message, nether_to_overworld):
	coords = message.commandLine.split(",")
	if len(coords) == 2:
		coords = [coords[0], 65, coords[1]]
	elif len(coords) == 1:
		if message.GetArg(0):
			(player, duplicates) = dynmap.GetPlayer(message.GetArg(0))
			if duplicates:
				message.Reply("There is more than one player matching {0}".format(message.GetArg(0)))
				return
			elif not player:
				message.Reply("Player is hidden from dynmap or not online")
				return

			coords = tuple(map(int, (player['x'], player['y'], player['z'])))
			dimension = player['world']
			if dimension == "world_the_end":
				message.Reply("Cannot convert end coordinates to nether")
				return
			elif dimension == "world_nether" and not nether_to_overworld:
				message.Reply("That player is already in the nether (Did you mean to use !!overworldloc?)")
				return
			elif dimension == "world" and nether_to_overworld:
				message.Reply("That player is already in the overworld (Did you mean to use !!netherloc?)")
				return
	
	try:
		coords = tuple(map(int, coords))
	except ValueError:
		message.Reply("Coordinates must be valid integers")
		return
	if len(coords) != 3:
		message.Reply("Missing coordinate, coordinates must be (x,z), (x,y,z) or (player name)")
		return
	
	multi = 1 / 8
	if nether_to_overworld :
		multi = 8
		
	message.Reply("({}, {}, {})    ({}, {}, {} to {})".format(
		coords[0] * multi, coords[1], coords[2] * multi,
		coords[0], coords[1], coords[2],
		"overworld" if nether_to_overworld else "nether"
	))
		
@command("netherloc", minArgs = 1)
def Netherloc(message):
	"""(netherloc <coordinates | player>). Converts overworld location to nether"""
	location_conversion(message, False)

@command("overworldloc", minArgs = 1)
def Overworldloc(message):
	"""(overworldloc <coordinates | player>). Converts nether location to overworld"""
	location_conversion(message, True)		
	
@command("brew", minArgs = 1)
def Brew(message):
	"""(brew <potion>). Give potion recipe for <potion>"""
	name = message.commandLine.lower()
	pot_type = ""
	extension = "none" # none | time | potency
	throw = "none" # none | splash | lingering
	
	pot_name_map = [
		["weak", "weakness"],
		["slow fall", "slow falling"],
		["turtle", "turtle master"],
		["invis", "invisibility"],
		["night vision", "night vision"],
		["breath", "water breathing"],
		["fire res", "fire resistance"],
		["regen", "regeneration"],
		["poison", "poison"],
		["harm", "harming"],
		["heal", "healing"],
		["strength", "strength"],
		["leap", "leaping"],
		["slow", "slowness"],
		["swift", "swiftness"],
		["speed", "swiftness"]
	]
	
	pot_ingredient_map = {
		"": [],
		"weakness": ["fermented spider eye"],
		"slow falling": ["phantom membrane"],
		"turtle master": ["turtle shell"],
		"invisibility": ["golden carrot", "fermented spider eye"],
		"night vision": ["golden carrot"],
		"water breathing": ["pufferfish"],
		"fire resistance": ["magma cream"],
		"regeneration": ["ghast tear"],
		"poison": ["spider eye"],
		"harming": ["glistering melon", "fermented spider eye"],
		"healing": ["glistering melon"],
		"strength": ["blaze powder"],
		"leaping": ["rabbit's foot"],
		"slowness": ["sugar", "fermented spider eye"],
		"swiftness": ["sugar"]
	}
	
	for pot in pot_name_map:
		if pot[0] in name:
			if pot_type != "":
				message.Reply("Ambigious potion type")
				return
			pot_type = pot[1]
	
	if any(x in name for x in ["extended", "time", "+"]):
		extension = "time"
	if any(x in name for x in ["2", "ii", "4", "iv"]):
		if extension != "none":
			message.Reply("Conflicting potion extension (time and potency)")
			return
		extension = "potency"
		
	if "splash" in name:
		throw = "splash"
	if "linger" in name:
		if throw != "none":
			message.Reply("Conflicting potion type (lingering and splash)")
			return
		throw = "lingering"
	
	steps = ["water bottle"]
	if pot_type != "weakness" and pot_type:
		steps.append("nether wart")
	steps += pot_ingredient_map[pot_type]
	
	if extension == "time":
		steps.append("redstone")
	elif extension == "potency":
		steps.append("glowstone")
		
	if throw != "none":
		steps.append("gunpowder")
	if throw == "lingering":
		steps.append("dragon's breath")
		
	message.Reply(" -> ".join(steps))


class Dynmap(object):
	lastFetched = 0
	data = None
	lastClaimFetched = {}
	claimData = {}
	DAY_START = 22812
	DAY_START_RAIN = 23031
	NIGHT_START = 13187
	NIGHT_START_RAIN = 12969

	def __init__(self):
		self.sizeRegex = r"<strong>W<\/strong>:(\d+)\s+<strong>H<\/strong>:(\d+)\s+<strong>S<\/strong>:(\d+)<br>"
		self.buildTrustRegex = r"<strong>Trust:<\/strong><br> (.*?)<br>"
		self.containerTrustRegex = r"<strong>Container Trust:<\/strong><br> (.*?)<br>"
		self.acessTrustRegex = r"<strong>Access Trust:<\/strong><br> (.*?)<br>"
		self.permissionTrustRegex = r"<strong>Permission Trust:<\/strong><br> (.*?)<br>"

	def _UpdateData(self):
		if time.time() > self.lastFetched+5:
			page = GetPage("{0}/up/world/world/".format(GetSetting(__name__, "dynmap-url")))
			self.data = json.loads(page)
			self.lastFetched = time.time()

	def _UpdateClaimData(self, dimension):
		if dimension not in self.lastClaimFetched or time.time() > self.lastClaimFetched[dimension]+5:
			page = GetPage("{0}/tiles/_markers_/marker_{1}.json".format(GetSetting(__name__, "dynmap-url"), dimension))
			self.claimData[dimension] = json.loads(page)
			self.lastClaimFetched[dimension] = time.time()

	def GetData(self):
		self._UpdateData()
		return self.data

	def GetClaimData(self, dimension):
		self._UpdateClaimData(dimension)
		return self.claimData[dimension]

	def GetClaimAtLocation(self, dimension, loc):
		data = self.GetClaimData(dimension)
		if not data:
			return None, True
		claims = data["sets"]["griefprevention.markerset"]["areas"]
		claim = None
		subclaim = None
		for claim in claims:
			claimposx = list(map(int, claims[claim]['x']))
			claimposz = list(map(int, claims[claim]['z']))
			if loc[0] in range(claimposx[0], claimposx[2]+1) and loc[2] in range(claimposz[0], claimposz[1]+1):
				return claims[claim], False
		return None, False

	def ParseClaimData(self, data):
		size = re.search(self.sizeRegex, data)
		access = re.search(self.acessTrustRegex, data)
		container = re.search(self.containerTrustRegex, data)
		build = re.search(self.buildTrustRegex, data)
		permission = re.search(self.permissionTrustRegex, data)

		sizeStr = size and "{0}x{1} ({2})".format(size.group(1), size.group(2), size.group(3)) or ""
		accessStr = access and access.group(1) or ""
		containerStr = container and container.group(1) or ""
		buildStr = build and build.group(1) or ""
		permissionStr = permission and permission.group(1) or ""
		return sizeStr, accessStr, containerStr, buildStr, permissionStr

	def GetPlayer(self, player):
		player = player.lower()
		data = self.GetData()
		playerList = data['players']
		matches = []
		for pl in playerList:
			if pl['name'].lower() == player:
				return pl, False
			elif pl['name'].lower().startswith(player):
				matches.append(pl)
		if len(matches) == 1:
			return matches[0], False
		elif len(matches) > 1:
			return None, True
		else:
			return None, False

	def GetPlayerNames(self):
		data = self.GetData()
		playerList = data['players']
		players = []
		for pl in playerList:
			players.append(pl['name'])
		players.sort()
		return players

	def GetTime(self):
		data = self.GetData()
		servertime = data["servertime"]
		CanSleep = False

		hours = servertime / 1000
		minutes = (hours - math.floor(hours)) * 60
		hours = (hours + 6) % 24
		formatted_time = "{0:02}:{1:02}{2}".format(int((hours-1)%12+1), int(minutes), "AM" if hours < 12 else "PM")
		if servertime >= self.NIGHT_START and servertime <= self.DAY_START:
			CanSleep = True
		elif data["isThundering"]:
			CanSleep = True
		return {"time": formatted_time, "serverTime": servertime, "canSleep": CanSleep}

	def GetWeather(self):
		data = self.GetData()
		return {"isThundering" : data["isThundering"], "hasStorm" : data["hasStorm"]}

dynmap = Dynmap()

@command("getplayer")
def GetPlayer(message):
	"""(getplayer [<player>]). Returns information on a player (lists all visible players if no args given)"""
	if message.GetArg(0):
		(player, duplicates) = dynmap.GetPlayer(message.GetArg(0))
		if duplicates:
			message.Reply("There is more than one player matching {0}".format(message.GetArg(0)))
			return
		elif not player:
			message.Reply("Player is hidden from dynmap or not online")
			return
		name = player['name']
		pos = tuple(map(int, (player['x'], player['y'], player['z'])))
		health = player['health']
		dimension = player['world']
		if dimension == "world_the_end":
			dimension = "The End"
		elif dimension == "world_nether":
			dimension = "The Nether"
		elif dimension == "world":
			dimension = "The Overworld"
		message.Reply("{0} is in {1} at ({2}, {3}, {4}), and has {5} health".format(name, dimension, pos[0], pos[1], pos[2], health))
	else:
		players = dynmap.GetPlayerNames()
		if not players:
			message.Reply("Nobody is visible on dynmap right now")
			return
		message.Reply("Players currently visible on dynmap: " + ", ".join(players))

@command("getmap")
def GetMap(message):
	"""(getmap (<player> [3D|cave] | <coordinates> [world|nether|end] [3D|cave]). Returns a dynmap link for the player or coordintes given."""
	arg = message.GetArg(0)
	if not arg:
		if message.isMinecraft:
			arg = message.mcusername
		else:
			raise ShowHelpException()

	(player, duplicates) = dynmap.GetPlayer(arg)
	if duplicates:
		message.Reply("There is more than one player matching {0}".format(arg))
		return
	elif not player:
		match = re.match("([\d-]+)[, ]{1,}([\d-]+)(?:[, ]{1,}([\d-]+))?(.*)", message.commandLine)
		if not match:
			message.Reply("Player is hidden from dynmap or not online")
			return
		# This is a coordinates getmap
		args = match.group(4).lower().split()
		dimension = "w"
		maptype = "f"
		if args:
			if args[0].find("nether") > -1:
				dimension = "n"
			elif args[0].find("end") > -1:
				dimension = "e"
		if len(args) > 1:
			if args[1] == "3d" or args[1] == "surface":
				maptype = "s"
			elif args[1] == "cave" and dimension == "w":
				maptype = "c"
		message.Reply("http://starcatcher.us/s?mc={0}{1}{2}{3},{4}".format(dimension, maptype, 5, match.group(1), match.group(3) or match.group(2)))
		return
	# Normal player getmap
	name = player['name']
	pos = tuple(map(int, (player['x'], player['y'], player['z'])))
	health = player['health']
	dimension = player['world']
	maptype = "f" #flat
	if message.GetArg(1):
		if message.GetArg(1).upper() == "3D" or message.GetArg(1).lower() == "surface":
			maptype = "s" #surface
		elif message.GetArg(1).lower() == "cave" and dimension == "world":
			maptype = "c" #cave
	#message.Reply("http://dynmap.starcatcher.us/?worldname={0}&mapname={1}&zoom=5&x={2}&y={3}&z={4}".format(dimension, maptype, pos[0], pos[1], pos[2]))
	message.Reply("http://starcatcher.us/s?mc={0}{1}{2}{3},{4}".format(dimension.split("_")[-1][0], maptype, 5, pos[0], pos[2]))

@command("getclaim")
def GetClaim(message):
	"""(getclaim <player>). Returns information on the claim <player> is standing in"""
	arg = message.GetArg(0)
	if not arg:
		if message.isMinecraft:
			arg = message.mcusername
		else:
			raise ShowHelpException()

	(player, duplicates) = dynmap.GetPlayer(arg)
	if duplicates:
		message.Reply("There is more than one player matching {0}".format(arg))
		return
	elif not player:
		message.Reply("Player is hidden from dynmap or not online")
		return
	(claim, error) = dynmap.GetClaimAtLocation(player['world'], (player['x'], player['y'], player['z']))
	if error:
		message.Reply("Error getting claim information for {0}".format(player['world']))
		return
	elif not claim:
		message.Reply("{0} is not currently inside any claims".format(player['name']))
		return
	(size, access, container, build, permission) = dynmap.ParseClaimData(claim['desc'])
	endStr = []
	if permission:
		endStr.append("\u000303Permission:\u0003 {0}".format(permission))
	if build:
		endStr.append("\u000303Build:\u0003 {0}".format(build))
	if container:
		endStr.append("\u000303Container:\u0003 {0}".format(container))
	if access:
		endStr.append("\u000303Access:\u0003 {0}".format(access))
	message.Reply("{0} is standing in a {1} claim by {2}. {3}".format(player['name'], size, claim['label'], "; ".join(endStr)))

@command("gettime")
def GetTime(message):
	data = dynmap.GetTime()
	time = data["time"]

	# Calculate IRL time until next phase
	serverTime = data["serverTime"]
	isDay = True
	if serverTime > dynmap.DAY_START:
		serverTime = serverTime - 24000
	if serverTime < dynmap.NIGHT_START:
		phasetime = math.floor((dynmap.NIGHT_START-serverTime)/20)
	else:
		isDay = False
		phasetime = math.floor((dynmap.DAY_START-serverTime)/20)

	message.Reply("The current minecraft time is {0}. {1:02}:{2:02} minutes until {3}.{4}".format(time, math.floor(phasetime//60), phasetime%60, "night" if isDay else "day", " (you can sleep)" if data["canSleep"] else ""))

@command("getweather")
def GetTime(message):
	data = dynmap.GetWeather()
	if data["isThundering"]:
		message.Reply("It is a thunderstorm")
	elif data["hasStorm"]:
		message.Reply("It is raining")
	else:
		message.Reply("It is clear")

@command("brewingchart")
def BrewingChart(message):
	message.Reply("https://hydra-media.cursecdn.com/minecraft.gamepedia.com/7/7b/Minecraft_brewing_en.png")

@command("tradingchart")
def TradingChart(message):
	message.Reply("https://i.imgur.com/cmXw3Lv.png")

@command("registerusername", minArgs=1, admin=True)
def RegisterUsername(message):
	"""(registerplayer <mcusername> <tptusername>). Sets the TPT username of a minecraft player."""
	if message.GetArg(1):
		StoreData(__name__, "usernamemap.{0}".format(message.GetArg(0)), message.GetArg(1))
	else:
		StoreData(__name__, "usernamemap.{0}".format(message.GetArg(0)), False)
	message.Reply("Done.")

@command("getusername", minArgs=1)
def GetUsername(message):
	tptusername = GetData(__name__, "usernamemap.{0}".format(message.GetArg(0)))
	if tptusername:
		message.Reply("{0}'s TPT username is {1}".format(message.GetArg(0), tptusername))
	else:
		message.Reply("Could not find player with that username")

def RunRconCommand(message, command):
	if not has_rcon:
		if rcon_error:
			message.Reply("error while connecting to rcon server")
		else:
			message.Reply("https://raw.githubusercontent.com/frostschutz/SourceLib/master/SourceRcon.py needs to be installed to use rcon")
		return False
	try:
		ret = rcon.rcon(command)
	except SourceRcon.SourceRconError:
		message.Reply("Error while running Rcon command")
		return False
	except OSError:
		message.Reply("Socket error while running Rcon command")
		return False
	return ret

def GetCurrentTeam(mcusername):
	allteammembers = GetData(__name__, "teammembers")
	if not allteammembers:
		return None
	for tname, teammembers in allteammembers.items():
		if mcusername in teammembers:
			return tname
	return None

@command("rcon", admin=True)
def Rcon(message):
	ret = RunRconCommand(message, message.commandLine)
	if ret == "":
		message.Reply("No output.")
	elif ret:
		message.Reply(ret)

@command("addteam", admin=True, minArgs=2)
def AddTeam(message):
	"""(addteam <owner> <teamname>). Adds a minecraft team. Admin only."""
	teamowner = message.GetArg(0)
	teamname = message.GetArg(1)
	#teamdisplayname = message.GetArg(2, endLine=True)
	if not RunRconCommand(message, "team add {0}".format(teamname)):
		return
	if not RunRconCommand(message, "team join {0} {1}".format(teamname, teamowner)):
		return
	StoreData(__name__, "teamowners.{0}".format(teamowner), teamname)
	StoreData(__name__, "teammembers.{0}".format(teamname), [teamowner])
	message.Reply("Added team {0} with owner {1}".format(teamname, teamowner))

@command("addteamowner", minArgs=1)
def AddTeamOwner(message):
	"""(addteamowner [<teamname>] <user>). Adds a new owner to your team."""
	if message.isMinecraft:
		username = message.mcusername
		teamname = GetData(__name__, "teamowners.{0}".format(username))
		if not teamname:
			message.Reply("You aren't the owner of any teams")
			return
		newowner = message.GetArg(0)
	elif CheckAdmin(message.fullhost):
		teamname = message.GetArg(0)
		newowner = message.GetArg(1)
	else:
		message.Reply("This command must be run in game")
		return
	teammembers = GetData(__name__, "teammembers.{0}".format(teamname))
	if not teammembers:
		message.Reply("No such team: {0}".format(teamname))
		return
	if newowner not in teammembers:
		message.Reply("{0} needs to be in team {1} to be an owner".format(newowner, teamname))
		return
	StoreData(__name__, "teamowners.{0}".format(newowner), teamname)
	message.Reply("Added {0} as owner for team {1}".format(newowner, teamname))

@command("removeteamowner", minArgs=1)
def RemoveTeamOwner(message):
	"""(removeteamowner [<teamname>] <user>). Removes an owner from your team."""
	if message.isMinecraft:
		username = message.mcusername
		teamname = GetData(__name__, "teamowners.{0}".format(username))
		if not teamname:
			message.Reply("You aren't the owner of any teams")
			return
		remowner = message.GetArg(0)
	elif CheckAdmin(message.fullhost):
		teamname = message.GetArg(0)
		remowner = message.GetArg(1)
	else:
		message.Reply("This command must be run in game")
		return
	remname = GetData(__name__, "teamowners.{0}".format(remowner))
	if remname != teamname:
		message.Reply("{0} isn't in team {1}".format(remowner, teamname))
		return
	DelData(__name__, "teamowners.{0}".format(remowner))
	message.Reply("Removed {0} as owner for team {1}".format(remowner, teamname))

@command("addmember", minArgs=1, admin=True)
def AddMember(message):
	"""(addmember <teamname> <user>). Adds a member to a team. Admin only."""
	teamname = message.GetArg(0)
	newmember = message.GetArg(1)
	allteammembers = GetData(__name__, "teammembers")
	if not allteammembers:
		messages.Reply("No teams exist!")
		return
	curteam = GetCurrentTeam(newmember)
	if curteam:
		message.Reply("{0} is already in team {1}".format(newmember, curteam))
		return
	if not RunRconCommand(message, "team join {0} {1}".format(teamname, newmember)):
		return
	StoreData(__name__, "teammembers.{0}".format(teamname), allteammembers[teamname] + [newmember])
	message.Reply("Added {0} to team {1}".format(newmember, teamname))

@command("remmember", minArgs=1)
def RemMember(message):
	"""(remmember <teamname> <user>). Removes a member from a team."""
	if message.isMinecraft:
		username = message.mcusername
		teamname = GetData(__name__, "teamowners.{0}".format(username))
		if not teamname:
			message.Reply("You aren't the owner of any teams")
			return
		remmember = message.GetArg(0)
	elif CheckAdmin(message.fullhost):
		teamname = message.GetArg(0)
		remmember = message.GetArg(1)
	else:
		message.Reply("This command must be run in game")
		return

	teammembers = GetData(__name__, "teammembers.{0}".format(teamname))
	if not teammembers:
		message.Reply("No such team: {0}".format(teamname))
		return
	if remmember not in teammembers:
		message.Reply("{0} isn't in team {1}".format(remmember, teamname))
		return
	if not RunRconCommand(message, "team leave {0}".format(remmember)):
		return
	teammembers.remove(remmember)
	StoreData(__name__, "teammembers.{0}".format(teamname), teammembers)

	#Also check if user was an owner
	ownercheck = GetData(__name__, "teamowners.{0}".format(remmember))
	if ownercheck == teamname:
		DelData(__name__, "teamowners.{0}".format(remmember))

	message.Reply("Removed {0} from team {1}".format(remmember, teamname))

@command("invitemember", minArgs=1)
def InviteMember(message):
	"""(invitemember <mcusername>). Invites a member to your team, if you are a team owner."""
	if not message.isMinecraft:
		message.Reply("This command must be run in game")
		return
	username = message.mcusername
	teamname = GetData(__name__, "teamowners.{0}".format(username))
	if not teamname:
		message.Reply("You aren't the owner of any teams")
		return

	# Max of 8 members
	teammembers = GetData(__name__, "teammembers.{0}".format(teamname))
	if len(teammembers) > 7:
		message.Reply("You have too many members on your team and cannot invite any more")
		return

	invitee = message.GetArg(0)
	curteam = GetCurrentTeam(invitee)
	if curteam:
		message.Reply("{0} is already in team {1}".format(invitee, curteam))
		return
	StoreData(__name__, "teaminvites.{0}.{1}".format(teamname, invitee), time.time()+1200)

	message.Reply("Invited {0} to team {1}".format(invitee, teamname))

@command("jointeam", minArgs=1)
def JoinTeam(message):
	"""(jointeam <teamname>). Join a team, you must be invited first."""
	if not message.isMinecraft:
		message.Reply("This command must be run in game")
		return
	username = message.mcusername
	teamname = message.GetArg(0)
	teammembers = GetData(__name__, "teammembers.{0}".format(teamname))
	if not teammembers:
		message.Reply("No such team exists")
		return
	invite = GetData(__name__, "teaminvites.{0}.{1}".format(teamname, username))
	if not invite:
		message.Reply("You need to be invited to team {0} first".format(teamname))
		return
	curteam = GetCurrentTeam(username)
	if curteam:
		message.Reply("You are already in team {0}".format(username, curteam))
		DelData(__name__, "teaminvites.{0}.{1}".format(teamname, username))
		return
	if invite < time.time():
		message.Reply("Invite is already expired")
		DelData(__name__, "teaminvites.{0}.{1}".format(teamname, username))
		return

	# Max of 8 members
	if len(teammembers) > 7:
		message.Reply("This team has too many members and cannot hold any more")
		return

	if not RunRconCommand(message, "team join {0} {1}".format(teamname, username)):
		return
	StoreData(__name__, "teammembers.{0}".format(teamname), teammembers + [username])
	DelData(__name__, "teaminvites.{0}.{1}".format(teamname, username))
	message.Reply("Added {0} to team {1}".format(username, teamname))

@command("leaveteam", minArgs=1)
def LeaveTeam(message):
	"""(leaveteam <teamname>). Leave a team."""
	if not message.isMinecraft:
		message.Reply("This command must be run in game")
		return
	username = message.mcusername
	teamname = message.GetArg(0)
	teammembers = GetData(__name__, "teammembers.{0}".format(teamname))
	if not teammembers:
		message.Reply("No such team exists")
		return
	if username not in teammembers:
		message.Reply("You aren't in team {0}".format(teamname))
		return
	if not RunRconCommand(message, "team leave {0}".format(username)):
		return
	teammembers.remove(username)
	StoreData(__name__, "teammembers.{0}".format(teamname), teammembers)

	#Also check if user was an owner
	ownercheck = GetData(__name__, "teamowners.{0}".format(username))
	if ownercheck == teamname:
		DelData(__name__, "teamowners.{0}".format(username))

	message.Reply("Removed yourself from team {0}".format(teamname))

@command("listmembers", minArgs=1)
def ListMembers(message):
	teamname = message.GetArg(0)
	teammembers = GetData(__name__, "teammembers.{0}".format(teamname))
	if not teammembers:
		message.Reply("No such team exists")
		return
	withowners = ["\u000303{0}\u0003".format(teammember) if GetData(__name__, "teamowners.{0}".format(teammember)) == teamname else teammember for teammember in teammembers]
	message.Reply("Members in team {0}: {1}".format(teamname, ", ".join(withowners)))

@command("friendlyfire", minArgs=1)
def FriendlyFire(message):
	"""(friendlyfire [<teamname>] true|false). Sets friendlyfire option for your team."""
	if message.isMinecraft:
		username = message.mcusername
		teamname = GetData(__name__, "teamowners.{0}".format(username))
		if not teamname:
			message.Reply("You aren't the owner of any teams")
			return
		setting = message.GetArg(0)
		# Teamname is supposed to be admin-only, but people will put it anyway, so ignore it
		if setting == teamname:
			setting = message.GetArg(1)
	elif CheckAdmin(message.fullhost):
		teamname = message.GetArg(0)
		setting = message.GetArg(1)
	else:
		message.Reply("This command must be run in game")
		return
	if not setting or (setting.lower() != "false" and setting.lower() != "true"):
		raise ShowHelpException()
	if RunRconCommand(message, "team modify {0} friendlyFire {1}".format(teamname, setting.lower())):
		message.Reply("Set friendlyfire for team {0} to {1}".format(teamname, setting.lower()))

