# Version 4 of the OpenAI-Discord bridge.
#
# This example requires the 'message_content' intent set on the bot.

import asyncio
import discord

from settings import Settings, DefaultFile
from api import API, Chat, ChatRole



# This is a little helper function used for running the chat as an async func
def chatReply(chat, msg):
	return chat.reply(msg)

# Helper function to get the chat if we're allowed to use this channel
def getChat(chanId, chats, api, settings):
	if chanId not in settings.channels:
		# No chat if we're not registered
		return None
	if chanId not in chats:
		chats[chanId] = Chat(api)
	return chats[chanId]

async def processCommands(message, chats, api, settings):
	msg = message.content.strip()
	cmd = msg.split()
	if len(cmd) < 2 or not cmd[0].startswith("$"):
		return False
	if cmd[1] != f"<@{settings.clientId}>":
		# It's a command, it's just not ours
		return True
	msg = msg.replace(cmd[0], "", 1).replace(cmd[1], "", 1).strip()
	cmd = cmd[0]
	chanId = message.channel.id
	
	if cmd == "$help":
		help_text = "Format: $<cmd> @<bot> <params>\n\n" \
					"$help - List available commands\n" \
					"$ping - Test if the bot is responding\n" \
					"$register - Make the bot listen in this channel\n" \
					"$remove - Stop the bot from replying in this channel\n" \
					"$reset - Clear conversation history in this channel\n" \
					"$speak - Have the bot say something\n" \
					"$whisper - Have the bot say something without remembering it"
		await message.channel.send(help_text)
	elif cmd == "$ping":
		await message.channel.send("Pong!")
	elif cmd == "$register":
		if chanId not in settings.channels:
			settings.channels.add(chanId)
			settings.save()
			await message.channel.send("Hello!")
		else:
			await message.channel.send("I'm already in this channel.")
	elif cmd == "$remove":
		if chanId in settings.channels:
			settings.channels.remove(chanId)
			settings.save()
			await message.channel.send("Bye.")
		else:
			await message.channel.send("I wasn't in this channel.")
	elif cmd == "$reset":
		chat = getChat(chanId, chats, api, settings)
		if chat is None:
			return True
		chat.history = []
		await message.channel.send("*Awakens from a coma unable to remember anything.*")
	elif cmd == "$speak":
		chat = getChat(chanId, chats, api, settings)
		if chat is None:
			return True
		chat.addHistory(ChatRole.ASSISTANT, msg)
		await message.channel.send(msg)
	elif cmd == "$whisper":
		chat = getChat(chanId, chats, api, settings)
		if chat is None:
			return True
		await message.channel.send(msg)
	else:
		# No valid commands detected
		return False
	
	return True



if __name__ == "__main__":
	settings_file = input(f"Settings file [{DefaultFile}]: ")
	if not settings_file:
		settings = Settings()
	else:
		settings = Settings(settings_file)
	
	api = API(settings)
	
	chats = {} # channelId: Chat
	
	intents = discord.Intents.default()
	intents.message_content = True
	intents.typing = False
	intents.presences = False
	
	client = discord.Client(intents=intents)
	
	@client.event
	async def on_ready():
		# Update runtime settings
		settings.clientId = client.user.id
		settings.name = client.user.name
		print(f'Logged in as {client.user}')
	
	@client.event
	async def on_message(message):
		# Ignore bot's own messages
		if message.author == client.user:
			return
		
		# Process any commands
		# This needs to go first to handle registration commands.
		isCommand = await processCommands(message, chats, api, settings)
		if isCommand:
			return
		
		chat = getChat(message.channel.id, chats, api, settings)
		# Ignore messages from channels that we're not in
		if chat is None:
			return
		
		msg = message.clean_content
		print(f"MSG: {msg}")
		
		async with message.channel.typing():
			loop = asyncio.get_event_loop()
			response = await loop.run_in_executor(None, chatReply, chat, msg)
		
		print(f"RESP: {response}")
		print()
		await message.channel.send(response)
	
	client.run(settings.token)
