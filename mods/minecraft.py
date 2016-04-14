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

@command("craft", minArgs = 1)
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