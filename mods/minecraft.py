import time
import json
from common import *

RegisterMod(__name__)

class CraftingList(object):
	recipes = {}
	def __init__(self):
		craftinglisttxt = open("mods/minecraft-craftinglist.txt")
		lines = craftinglisttxt.readlines()
		craftinglisttxt.close()
		for line in lines:
			if not len(line) or line[0] != ' ':
				continue
			item = line.lower().split('|')[0].strip()
			recipelines = line.lower().split('|')[1].split('/')

			self.recipes[item] = []
			for something in recipelines:
				self.recipes[item].append([a.strip() for a in something.split('-')])
	
	def PrintRecipe(self, name):
		if not name in self.recipes:
			return "Couldn't find recipe, try using {0}search".format(commandChar)
		recipe = self.recipes[name]
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
			output += "\n"
		return output.strip()
	
	def _SearchRecipeInner(self, recipe, name):
		for i in recipe:
			for j in i:
				if name == j:
					return name
		
	def SearchRecipe(self, name):
		exactMatches = []
		closeMatches = []
		badMatches = []
		for recipe in self.recipes:
			if name == recipe:
				exactMatches.append(recipe)
			elif name in recipe:
				closeMatches.append(recipe)
			else:
				match = self._SearchRecipeInner(self.recipes[recipe], name)
				if match:
					badMatches.append(recipe)
		if len(exactMatches) or len(closeMatches) or len(badMatches):
			return ", ".join(exactMatches+closeMatches+badMatches)
		else:
			return "No matches"

recipes = CraftingList()

@command("craft", minArgs = 1, rateLimit=True)
def Craft(username, hostmask, channel, text, account):
	"""(craft <item>). Prints a minecraft crafting recipe"""
	output = recipes.PrintRecipe(" ".join(text[0:]))
	for line in output.splitlines():
		SendMessage(channel, line)

@command("search", minArgs = 1)
def Search(username, hostmask, channel, text, account):
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

dynmap = Dynmap()

@command("getplayer")
def GetPlayer(username, hostmask, channel, text, account):
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
def GetMap(username, hostmask, channel, text, account):
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
def GetClaim(username, hostmask, channel, text, account):
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
		SendMessage(channel, "{0} is not currently inside any claims (temp: {1})".format(player['name'], player['world']))
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
