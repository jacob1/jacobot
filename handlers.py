import os
import importlib
import sys
import traceback

class ReloadedModuleException(Exception):
	pass

plugins = {}
def LoadMods():
	print("Loading modules")
	loaded = []
	failed = []

	plugins["config"] = importlib.import_module("config")
	globals().update(plugins["config"].GetGlobals())
	plugins["common"] = importlib.import_module("common")
	globals().update(plugins["common"].GetGlobals())

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

async def HandleMessage(client, message):

	# Ignore our own messages
	if message.author == client.user:
		return 
	message = Message(client, message)
	if not message.isCommand:
		return

	for mod in commands:
		for i in commands[mod]:
			if message.command == i[0]:
				try:
					await i[1](message)
				except plugins["common"].ShowHelpException:
					if i[1].__doc__:
						await message.Reply("Usage: %s" % (i[1].__doc__))
					else:
						await message.Reply("Invalid arguments (no help text available)")
				return

	#TODO: all of this should be moved into an admin plugin
	if not message.sender.IsAdmin():
		return

	if message.command == "reload":
		plugin_name = message.GetArg(0)
		if not plugin_name:
			await message.Reply("Usage: reload <plugin name>")
			return

		if plugin_name in commands:
			commands[plugin_name] = []

		if plugin_name == "config":
			del sys.modules["config"]
			plugins["config"] = importlib.import_module("config")
			globals().update(plugins["config"].GetGlobals())
			#plugins["common"].adminHostmasks = plugins["config"].adminHostmasks
			#plugins["common"].ownerHostmasks = plugins["config"].ownerHostmasks
			raise ReloadedModuleException({"message":f"Reloading {plugin_name}.py", "module":plugin_name, "channel":message.channel})
		elif plugin_name == "handlers" or plugin_name == "common":
			raise ReloadedModuleException({"message":f"Reloading {plugin_name}.py", "module":plugin_name, "channel":message.channel})

		if plugin_name not in plugins:
			await message.Reply(f"No such module: {plugin_name}")
			return
		if plugin_name in plugins["common"].commands:
			del plugins["common"].commands[plugin_name]
		plugins[plugin_name] = importlib.reload(plugins[plugin_name])
		
		await message.Reply("Reloaded {0}.py".format(plugin_name))

		return
	elif message.command == "load":
		plugin_name = message.GetArg(0)
		if not plugin_name:
			await message.Reply("Usage: load <plugin name>")
			return

		if plugin_name in plugins:
			await message.Reply(f"Module {plugin_name} already loaded")
			return

		try:
			plugins[plugin_name] = importlib.import_module(f"plugins.{plugin_name}")
		except ModuleNotFoundError:
			await message.Reply(f"Module not found: {plugin_name}.py")
			return
		await message.Reply(f"Loaded {plugin_name}.py")

		return
	elif message.command == "unload":
		plugin_name = message.GetArg(0)
		if not plugin_name:
			await message.Reply("Usage: unload <plugin name>")
			return

		if plugin_name not in plugins or plugin_name in ["common", "handlers", "config"]:
			await message.Reply("Module not loaded")
			return

		if plugin_name in plugins["common"].commands:
			del plugins["common"].commands[plugin_name]
		del plugins[plugin_name]
		del sys.modules["plugins.{0}".format(plugin_name)]

		await message.Reply(f"Unloaded {plugin_name}.py")

		return

