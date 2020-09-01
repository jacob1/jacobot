import asyncio
import importlib
import socket # For error handler. Use asyncio?
import sys
import traceback

try:
	config = importlib.import_module("config")
	globals().update(config.get_globals())
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

try:
	server = importlib.import_module("connection.server")
except Exception:
	print("Error loading connection/server.py, cannot start bot")
	print(traceback.format_exc())
	sys.exit(1)

#client = discord.Client()

#@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')
	#handlers.LoadMods()

# Find a channel or member in this server
# server should be full name of the server, like "TPT Unofficial Server"
# channel can be a channel name like "#bot-commands" or a user like "jacob1#8633"
def find_channel(server_name, channel_name):
	client = main_server.client
	search_server = None
	for c_server in client.guilds:
		if c_server.name == server_name:
			if search_server:
				raise Exception(f"Two servers match '{server}'")
			search_server = c_server
	if channel_name[0] == "#":
		stripped_channel_name = channel_name[1:]
		for s_channel in search_server.channels:
			if s_channel.name == stripped_channel_name:
				return s_channel
	user_split = channel_name.split("#")
	if len(user_split) == 2:
		for s_member in search_server.members:
			if s_member.name == user_split[0] and s_member.discriminator == user_split[1]:
				return s_member
	return None

def log_message(message):
	#if message.author == client.user:
	#	print("--> " + message.content)
	#else:
	print("<-- " + message)

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
	await chan.send(f"Error: {url} (admin link {admin})")

# Handle an error. Prints it to console, then calls upload_error to upload it
async def handle_error(context):
	tb = traceback.format_exc()
	print(f"=======ERROR=======\n{tb}========END========\n")
	if context:
		await context.reply("Error printed to console")
	if error_code:
		try:
			await upload_error(tb)
		except Exception:
			chan = find_channel(error_server, error_channel)
			if chan:
				await chan.send("We heard you like errors, so we put an error in your error handler so you can error while you catch errors")
			else:
				print(f"Could not find error channel! {error_server}, {error_channel}")
			print("=======ERROR=======\n{0}========END========\n".format(traceback.format_exc()))

async def on_message(event):
	try:
		await on_message_runner(event)
	except Exception:
		await handle_error(event.context)

async def on_message_runner(event):
	global common
	global config
	global handler

	context = event.context
	message = event.message
	log_message(message)

	try:
		await handler.HandleMessage(context, message)
	except handler.ReloadedModuleException as e:
		reload_module = e.args[0]["module"]
		reload_context = e.args[0]["context"]

		if reload_module == "config":
			globals().update(handler.plugins["config"].get_globals())
			await context.reply("Reloaded config.py")
		elif reload_module == "handlers":
			try:
				#common.WriteAllData(force=True)
				for modname, plugin in handler.plugins.items():
					if plugin.__name__ in sys.modules:
						del sys.modules[plugin.__name__]
				del sys.modules["handlers"]
				handler = importlib.import_module("handlers")
				common = importlib.import_module("common")
				_, failed = handler.LoadMods()
			except Exception as reload_exception:
				print(reload_exception)
			else:
				globals().update(handler.plugins["common"].get_globals())
				
				ret = "Reloaded handlers.py, common.py, and all plugins"
				if failed:
					ret += ". Failed plugins: " + ", ".join(failed)
				await context.reply(ret)
		elif reload_module == "common":
			#common.WriteAllData(force=True)
			for modname, plugin in handler.plugins.items():
				if plugin.__name__ in sys.modules:
					del sys.modules[plugin.__name__]
			common = importlib.import_module("common")
			_, failed = handler.LoadMods()
			ret = "Reloaded common.py and all plugins"
			if failed:
				ret += ". Failed plugins: " + ", ".join(failed)
			await context.reply(ret)

#Multiple bots in one asyncio:
#https://github.com/Rapptz/discord.py/issues/516

main_server = server.DiscordServer(botToken, on_message)

#host, port, ssl, nick, ident, account_name, account_password
irc_server = server.IrcServer(on_message, host="irc.freenode.net", port=6697, ssl=True, nick="potatobot", ident="jacobot")

clients = [irc_server, main_server]

loop = asyncio.get_event_loop()
try:
	task1 = loop.create_task(main_server.connect())
	loop.run_until_complete(irc_server.connect())
	task2 = loop.create_task(irc_server.main_loop())
	gathered = asyncio.gather(task1, task2, loop=loop)
	loop.run_until_complete(gathered)
except KeyboardInterrupt:
	#loop.run_until_complete(main_server.client.logout())
	loop.stop()

