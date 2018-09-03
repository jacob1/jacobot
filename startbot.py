import asyncio
import discord
import importlib
import socket # For error handler. Use asyncio?
import sys
import traceback

#https://github.com/Rapptz/discord.py
#https://discordpy.readthedocs.io/en/latest/api.html#discord.Message

try:
        config = importlib.import_module("config")
        globals().update(config.GetGlobals())
except Exception:
        print("Error loading config.py, cannot start bot")
        print(traceback.format_exc())
        sys.exit(1)

try:
	common = importlib.import_module("common")
except Exception:
	print("Error loading common.py, cannot start bot")
	print(traceback.format_exc())
	sys.exit(1)

try:
	handler = importlib.import_module("handlers")
	handler.LoadMods()
except Exception:
	print("Error loading handlers.py, cannot start bot")
	print(traceback.format_exc())
	sys.exit(1)

client = discord.Client()

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')
	#handlers.LoadMods()

# Find a channel or member in this server
# server should be full name of the server, like "TPT Unofficial Server"
# channel can be a channel name like "#bot-commands" or a user like "jacob1#8633"
def find_channel(server, channel):
	search_server = None
	for c_server in client.servers:
		if c_server.name == server:
			if search_server:
				raise Exception(f"Two servers match '{server}'")
			search_server = c_server
	if channel[0] == "#":
		stripped_channel = channel[1:]
		for s_channel in search_server.channels:
			if s_channel.name == stripped_channel:
				return s_channel
	user_split = channel.split("#")
	if len(user_split) == 2:
		for s_member in search_server.members:
			if s_member.name == user_split[0] and s_member.discriminator == user_split[1]:
				return s_member
	return None

def log_message(message):
	if message.author == client.user:
		print("--> " + message.content)
	else:
		print("<-- " + message.content)

# Upload an error to tcp.st, and print the link to the error channel defined in error_server / error_channel
async def upload_error(tb):
	sock = socket.create_connection(("tcp.st", 7777))
	sock.sendall(tb.encode("utf-8"))
	sock.settimeout(1)
	reply = b""
	while True:
	        try:
	                reply += sock.recv(4096)
	        except:
	                break
	url = {key: value for key, value, *_ in [line.split(b" ") + [None] for line in reply.split(b"\n") if line]}[b"URL"].decode("utf-8")
	admin = {key: value for key, value, *_ in [line.split(b" ") + [None] for line in reply.split(b"\n") if line]}[b"ADMIN"].decode("utf-8")

	chan = find_channel(error_server, error_channel)
	await client.send_message(chan, f"Error: {url} (admin link {admin})")

# Handle an error. Prints it to console, then calls upload_error to upload it
async def handle_error(channel):
	tb = traceback.format_exc()
	print(f"=======ERROR=======\n{tb}========END========\n")
	if channel:
		await client.send_message(channel, "Error printed to console")
	if error_code:
		try:
			await upload_error(tb)
		except Exception:
			chan = find_channel(error_server, error_channel)
			if chan:
				await client.send_message(chan, "We heard you like errors, so we put an error in your error handler so you can error while you catch errors")
			else:
				print(f"Could not find error channel! {error_server}, {error_channel}")
			print("=======ERROR=======\n{0}========END========\n".format(traceback.format_exc()))

@client.event
async def on_message(message):
	try:
		await on_message_runner(message)
	except Exception:
		await handle_error(message.channel)

async def on_message_runner(message):
	global common
	global config
	global handler

	log_message(message)

	try:
		await handler.HandleMessage(client, message)
	except handler.ReloadedModuleException as e:
		reloadedModule = e.args[0]["module"]

		if reloadedModule == "config":
			globals().update(handler.plugins["config"].GetGlobals())
			await client.send_message(message.channel, "Reloaded config.py")
		elif reloadedModule == "handlers":
			try:
				#common.WriteAllData(force=True)
				for modname, plugin in handler.plugins.items():
					if plugin.__name__ in sys.modules:
						del sys.modules[plugin.__name__]
				del sys.modules["handlers"]
				handler = importlib.import_module("handlers")
				common = importlib.import_module("common")
				_, failed = handler.LoadMods()
			except Exception as reloadException:
				#common.SetCurrentChannel(e.args[0]["channel"])
				#PrintError()
				#common.SetCurrentChannel(None)
				print(reloadException)
			else:
				globals().update(handler.plugins["common"].GetGlobals())
				#common.SetCurrentChannel(None)
				#common.SetRateLimiting(True)
				
				ret = "Reloaded handlers.py, common.py, and all plugins"
				if failed:
					ret += ". Failed plugins: " + ", ".join(failed)
				await client.send_message(message.channel, ret)
		elif reloadedModule == "common":
			#common.WriteAllData(force=True)
			for modname, plugin in handler.plugins.items():
				if plugin.__name__ in sys.modules:
					del sys.modules[plugin.__name__]
			common = importlib.import_module("common")
			#common.SetCurrentChannel(None)
			#common.SetRateLimiting(True)
			_, failed = handler.LoadMods()
			ret = "Reloaded common.py and all plugins"
			if failed:
				ret += ". Failed plugins: " + ", ".join(failed)
			await client.send_message(message.channel, ret)

client.run(botToken)

