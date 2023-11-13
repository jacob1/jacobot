import os
import importlib
import traceback
import typing

import config

if typing.TYPE_CHECKING:
	from common import CommandParser

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

async def HandleMessage(context, message : str) -> None:
	command_parser = CommandParser(message, config.command_char)
	try:
		command_parser.parse(context)
		if not command_parser.isCommand:
			return
		await command_parser.call(context)
	except plugins["common"].NoSuchCommandException as e:
		await context.reply_in_notice(e.message)
	except plugins["common"].AmbiguousException as e:
		await context.reply_in_notice(e.message)
	except plugins["common"].PermissionException as e:
		if e.message:
			await context.reply_in_notice(e.message)
	except plugins["common"].BadUserMatch as e:
		await context.reply_in_notice(e.message)
	except plugins["common"].ShowHelpException:
		if command_parser.subcommand:
			doc = command_parser.subcommand.get_help()
		else:
			doc = command_parser.command.get_help()
		if doc:
			await context.reply(f"Usage: {doc}")
		else:
			await context.reply("Invalid arguments (no help text available)")
