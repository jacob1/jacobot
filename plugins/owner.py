import importlib
import os
import sys

from common import *
import handlers

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from connection.context import Context

@command("restart", owner = True)
async def restart(context : "Context"):
	"""(restart) Restarts the bot."""

	print("Restarting bot due to restart command")
	os.execl(sys.executable, sys.executable, *sys.argv)

@command("reload", owner = True)
async def reload_cmd(context : "Context", plugin_name : str):
	"""(reload <plugin_name>) Reloads a plugin."""

	if plugin_name == "config":
		del sys.modules["config"]
		handlers.plugins["config"] = importlib.import_module("config")
		#handlers.get_globals().update(handlers.plugins["config"].GetGlobals())
		for (modname, mod) in sys.modules.items():
			#if hasattr(mod.__dict__, "loaded_config_py"):
			if "loaded_config_py" in mod.__dict__:
				print("Attempting to reload config.py for module " + modname)
				mod.__dict__.update(handlers.plugins["config"].__dict__)
		reload_obj = {"message":f"Reloading {plugin_name}.py", "module":plugin_name, "context":context}
		raise handlers.ReloadedModuleException(reload_obj)
	elif plugin_name == "handlers" or plugin_name == "common":
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
async def load_cmd(context : "Context", plugin_name : str):
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
async def unload_cmd(context : "Context", plugin_name : str):
	"""(unload <plugin_name>) Unloads a plugin."""

	if plugin_name not in handlers.plugins or plugin_name in ["common", "handlers", "config", "connection"]:
		await context.reply("Module not loaded")
		return

	if plugin_name in handlers.plugins["common"].commands:
		del handlers.plugins["common"].commands[plugin_name]
	del handlers.plugins[plugin_name]
	del sys.modules["plugins.{0}".format(plugin_name)]

	await context.reply(f"Unloaded {plugin_name}.py")

@command("eval", owner = True)
async def eval_cmd(context : "Context", *, code : str):
	try:
		formatted_code = code.replace("\\n", "\n").replace("\\t", "\t")
		ret = str(eval(formatted_code))
	except Exception as e:
		ret = str(type(e)) + ":" + str(e)

	await context.reply(f"Ret: {ret}")

@command("error", owner = True)
async def error_cmd(context : "Context"):
	await context.reply(str(0/0))
