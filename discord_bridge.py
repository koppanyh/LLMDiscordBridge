# Version 2 of the OpenAI-Discord bridge.
# Written by @koppanyh
#
# Setup:
# installer_files\conda\condabin\conda.bat activate installer_files\env
# python -m pip install -U discord.py
#
# This example requires the 'message_content' intent set on the bot.

import asyncio
import discord
import json
import os
import requests



class Settings:
	def __init__(self, fileName="discord_settings.json"):
		# Saved settings
		self.token = ""
		self.mode = ""
		self.character = ""
		self.url = "http://127.0.0.1:5000"
		self.channels = set()
		# Runtime settings
		self.fileName = fileName
		self.name = ""
		self.clientId = 0
	def load(self):
		with open(self.fileName, "r") as f:
			data = {
				"token": self.token,
				"mode": self.mode,
				"character": self.character,
				"url": self.url,
				"channels": list(self.channels)
			}
			data.update(json.loads(f.read()))
			self.token = data["token"]
			self.mode = data["mode"]
			self.character = data["character"]
			self.url = data["url"]
			self.channels = set(data["channels"])
	def save(self):
		data = {
			"token": self.token,
			"mode": self.mode,
			"character": self.character,
			"url": self.url,
			"channels": list(self.channels)
		}
		with open(self.fileName, "w") as f:
			f.write(json.dumps(data, indent=2))
	def loadSafe(self):
		# Load settings or fill them in if they don't exist
		if os.path.exists(self.fileName):
			self.load()
		else:
			self.token = input("Bot's Discord token: ")
			self.mode = input("LLM mode (chat/chat-instruct/instruct): ")
			self.character = input("LLM character name: ")
			self.url = input("OpenAI API endpoint (http://127.0.0.1:5000): ")
			self.save()



class API:
	headers = {
		"Content-Type": "application/json"
	}
	def __init__(self, server="http://127.0.0.1:5000"):
		self.url = server + "/v1/chat/completions"
	def chat(self, data):
		response = requests.post(self.url, headers=API.headers, json=data, verify=False)
		return response.json()['choices'][0]
		# {'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': "Hey! What's up?"}}

class Chat:
	def __init__(self, api, mode, character):
		self.api = api
		self.mode = mode
		self.character = character
		self.history = []
	def reply(self, msg):
		self.addHistory("user", msg)
		data = {
			"mode": self.mode,
			"character": self.character,
			"messages": self.history
		}
		response = api.chat(data)["message"]
		self.history.append(response)
		return response["content"]
	def addHistory(self, role, content):
		self.history.append({"role": role, "content": content})



# This is a little helper function used for running the chat as an async func
def chatReply(chat, msg):
	return chat.reply(msg)

# Helper function to get the chat if we're allowed to use this channel
def getChat(chanId, chats, api, settings):
	if chanId not in settings.channels:
		# No chat if we're not registered
		return None
	if chanId in chats:
		return chats[chanId]
	else:
		chat = Chat(api, settings.mode, settings.character)
		chats[chanId] = chat
		return chat

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
		await message.channel.send("$ping, $register, $remove, $reset, $speak, $whisper")
	elif cmd == "$ping":
		await message.channel.send("Pong!")
	elif cmd == "$register":
		settings.channels.add(chanId)
		settings.save()
		await message.channel.send("Hello!")
	elif cmd == "$remove":
		if chanId in settings.channels:
			settings.channels.remove(chanId)
			settings.save()
		await message.channel.send("Bye")
	elif cmd == "$reset":
		chat = getChat(chanId, chats, api, settings)
		if chat is not None:
			chat.history = []
			await message.channel.send("Wut?")
	elif cmd == "$speak":
		chat = getChat(chanId, chats, api, settings)
		if chat is not None:
			chat.addHistory("assistant", msg)
			await message.channel.send(msg)
	elif cmd == "$whisper":
		chat = getChat(chanId, chats, api, settings)
		if chat is not None:
			await message.channel.send(msg)
	else:
		# No valid commands detected
		return False
	
	return True



if __name__ == "__main__":
	settings = Settings("discord_settings.json")
	settings.loadSafe()
	
	api = API(settings.url)
	
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
		print('Please be aware that character greetings are not included in the generated prompts')
	
	@client.event
	async def on_message(message):
		# Ignore bot's own messages
		if message.author == client.user:
			return
		
		# Process any commands
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
