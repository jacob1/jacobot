import os
import importlib
import traceback

def get_globals():
	return globals()

class ReloadedModuleException(Exception):
	pass

plugins = {}
def LoadMods():
	print("Loading modules")
	loaded = []
	failed = []

	plugins["config"] = importlib.import_module("config")
	plugins["common"] = importlib.import_module("common")
	globals().update(plugins["common"].get_globals())

	for i in os.listdir("plugins"):
		if os.path.isfile(os.path.join("plugins", i)) and i[-3:] == ".py":# and i[:-3] not in disabledPlugins:
			try:
				print("Loading {} ...".format(i))
				plugins[i[:-3]] = importlib.import_module("plugins.{0}".format(i[:-3]))
				loaded.append(i[:-3])
			except Exception:
				print("Error loading {}".format(i))
				print(traceback.format_exc())
				failed.append(i[:-3])
				pass
	print("Done loading plugins")
	return loaded, failed

async def HandleMessage(context, message):

	command_parser = CommandParser(message)
	if not command_parser.isCommand:
		return

	for mod in commands:
		for i in commands[mod]:
			if command_parser.command == i[0]:
				try:
					await i[1](context, command_parser)
				except plugins["common"].ShowHelpException:
					if i[1].__doc__:
						await context.reply("Usage: %s" % (i[1].__doc__))
					else:
						await context.reply("Invalid arguments (no help text available)")
				except plugins["common"].PermissionException:
					await context.reply_in_notice("This command is owner-only")
				return

