import importlib
import sys
from typing import Optional

from common import *
import handlers

@command("reload", owner = True)
async def reload_cmd(context, plugin_name : str):
	"""(reload <plugin_name>) Reloads a plugin."""

	if plugin_name == "config":
		del sys.modules["config"]
		handlers.plugins["config"] = importlib.import_module("config")
		handlers.get_globals().update(handlers.plugins["config"].GetGlobals())
		reload_obj = {"message":f"Reloading {plugin_name}.py", "module":plugin_name, "context":context}
		raise handlers.ReloadedModuleException(reload_obj)
	elif plugin_name == "handlers" or plugin_name == "common" or plugin_name == "connection":
		reload_obj = {"message":f"Reloading {plugin_name}.py", "module":plugin_name, "context":context}
		raise handlers.ReloadedModuleException(reload_obj)

	if plugin_name not in handlers.plugins:
		await context.reply(f"No such module: {plugin_name}")
		return
	if plugin_name in handlers.plugins["common"].commands:
		del handlers.plugins["common"].commands[plugin_name]
	handlers.plugins[plugin_name] = importlib.reload(handlers.plugins[plugin_name])

	await context.reply("Reloaded {0}.py".format(plugin_name))

@command("load", owner = True)
async def load_cmd(context, plugin_name : str):
	"""(load <plugin_name>) Loads a plugin."""

	if plugin_name in ["common", "handlers", "config", "connection"]:
		await context.reply("That is a reserved plugin name and cannot be loaded")
		return
	if plugin_name in handlers.plugins:
		await context.reply(f"Module {plugin_name} already loaded")
		return

	try:
		handlers.plugins[plugin_name] = importlib.import_module(f"plugins.{plugin_name}")
	except ModuleNotFoundError:
		await context.reply(f"Module not found: {plugin_name}.py")
		return
	await context.reply(f"Loaded {plugin_name}.py")

@command("unload", owner = True)
async def unload_cmd(context, plugin_name : str):
	"""(unload <plugin_name>) Unloads a plugin."""

	if plugin_name not in handlers.plugins or plugin_name in ["common", "handlers", "config", "connection"]:
		await context.reply("Module not loaded")
		return

	if plugin_name in handlers.plugins["common"].commands:
		del handlers.plugins["common"].commands[plugin_name]
	del handlers.plugins[plugin_name]
	del sys.modules["plugins.{0}".format(plugin_name)]

	await context.reply(f"Unloaded {plugin_name}.py")

