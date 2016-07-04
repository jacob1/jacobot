import time
import json
import math

from common import *
RegisterMod(__name__)

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
		craftinglisttxt = open("mods/minecraft-craftinglist.txt")
		lines = craftinglisttxt.readlines()
		craftinglisttxt.close()
		for line in lines:
			if len(line) and line[0] == ' ':
				self._ParseItem(line)
			elif len(line) and line[0] == "=":
				self._ParseReplacement(line[1:])

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
def Craft(username, hostmask, channel, text):
	"""(craft <item>). Prints a minecraft crafting recipe"""
	output = recipes.PrintRecipe(" ".join(text[0:]))
	for line in output.splitlines():
		SendMessage(channel, line)

@command("search", minArgs = 1)
def Search(username, hostmask, channel, text):
	"""(search <item>). Searches for minecraft recipes matching or containing an item"""
	searchTerm = " ".join(text[0:])
	if len(searchTerm) < 3:
		SendMessage(channel, "Search text too short")
		return

	output = recipes.SearchRecipe(" ".join(text[0:]))
	for line in output.splitlines():
		SendMessage(channel, line)


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
			page = GetPage("http://dynmap.starcatcher.us/up/world/world/")
			self.data = json.loads(page)
			self.lastFetched = time.time()

	def _UpdateClaimData(self, dimension):
		if dimension not in self.lastClaimFetched or time.time() > self.lastClaimFetched[dimension]+5:
			page = GetPage("http://dynmap.starcatcher.us/tiles/_markers_/marker_{0}.json".format(dimension))
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
def GetPlayer(username, hostmask, channel, text):
	"""(getplayer [<player>]). Returns information on a player (lists all visible players if no args given)"""
	if len(text):
		(player, duplicates) = dynmap.GetPlayer(text[0])
		if duplicates:
			SendMessage(channel, "There is more than one player matching {0}".format(text[0]))
			return
		elif not player:
			SendMessage(channel, "Player is hidden from dynmap or not online")
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
		SendMessage(channel, "{0} is in {1} at ({2}, {3}, {4}), and has {5} health".format(name, dimension, pos[0], pos[1], pos[2], health))
	else:
		players = dynmap.GetPlayerNames()
		if not players:
			SendMessage(channel, "Nobody is visible on dynmap right now")
			return
		SendMessage(channel, "Players currently visible on dynmap: " + ", ".join(players))

@command("getmap", minArgs=1)
def GetMap(username, hostmask, channel, text):
	"""(getmap (<player> [3D|cave] | <coordinates> [world|nether|end] [3D|cave]). Returns a dynmap link for the player or coordintes given."""
	(player, duplicates) = dynmap.GetPlayer(text[0])
	if duplicates:
		SendMessage(channel, "There is more than one player matching {0}".format(text[0]))
		return
	elif not player:
		match = re.match("([\d-]+)[, ]{1,}([\d-]+)(?:[, ]{1,}([\d-]+))?(.*)", " ".join(text))
		if not match:
			SendMessage(channel, "Player is hidden from dynmap or not online")
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
		SendMessage(channel, "http://starcatcher.us/s?mc={0}{1}{2}{3},{4}".format(dimension, maptype, 5, match.group(1), match.group(3) or match.group(2)))
		return
	# Normal player getmap
	name = player['name']
	pos = tuple(map(int, (player['x'], player['y'], player['z'])))
	health = player['health']
	dimension = player['world']
	maptype = "f" #flat
	if len(text) > 1:
		if text[1].upper() == "3D" or text[1].lower() == "surface":
			maptype = "s" #surface
		elif text[1].lower() == "cave" and dimension == "world":
			maptype = "c" #cave
	#SendMessage(channel, "http://dynmap.starcatcher.us/?worldname={0}&mapname={1}&zoom=5&x={2}&y={3}&z={4}".format(dimension, maptype, pos[0], pos[1], pos[2]))
	SendMessage(channel, "http://starcatcher.us/s?mc={0}{1}{2}{3},{4}".format(dimension.split("_")[-1][0], maptype, 5, pos[0], pos[2]))

@command("getclaim", minArgs=1)
def GetClaim(username, hostmask, channel, text):
	"""(getclaim <player>). Returns information on the claim <player> is standing in"""
	(player, duplicates) = dynmap.GetPlayer(text[0])
	if duplicates:
		SendMessage(channel, "There is more than one player matching {0}".format(text[0]))
		return
	elif not player:
		SendMessage(channel, "Player is hidden from dynmap or not online")
		return
	(claim, error) = dynmap.GetClaimAtLocation(player['world'], (player['x'], player['y'], player['z']))
	if error:
		SendMessage(channel, "Error getting claim information for {0}".format(player['world']))
		return
	elif not claim:
		SendMessage(channel, "{0} is not currently inside any claims".format(player['name']))
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
	SendMessage(channel, "{0} is standing in a {1} claim by {2}. {3}".format(player['name'], size, claim['label'], "; ".join(endStr)))

@command("gettime")
def GetTime(username, hostmask, channel, text):
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

	SendMessage(channel, "The current minecraft time is {0}. {1:02}:{2:02} minutes until {3}.{4}".format(time, math.floor(phasetime//60), phasetime%60, "night" if isDay else "day", " (you can sleep)" if data["canSleep"] else ""))

@command("getweather")
def GetTime(username, hostmask, channel, text):
	data = dynmap.GetWeather()
	if data["isThundering"]:
		SendMessage(channel, "It is a thunderstorm")
	elif data["hasStorm"]:
		SendMessage(channel, "It is raining")
	else:
		SendMessage(channel, "It is clear")

@command("brewingchart")
def BrewingChart(username, hostmask, channel, text):
	SendMessage(channel, "https://hydra-media.cursecdn.com/minecraft.gamepedia.com/7/7b/Minecraft_brewing_en.png")
