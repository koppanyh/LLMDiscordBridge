# Version 1 of the OpenAI-Discord bridge.
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
	@staticmethod
	def checkSettings(fileName="discord_settings.json"):
		return os.path.exists(fileName)
	def __init__(self, fileName="discord_settings.json"):
		self.fileName = fileName
		self.token = ""
		self.mode = ""
		self.character = ""
		self.name = ""
		self.clientId = 0
		self.channels = set()
	def load(self):
		with open(self.fileName, "r") as f:
			data = json.loads(f.read())
			self.token = data["token"]
			self.mode = data["mode"]
			self.character = data["character"]
			self.name = data["name"]
			self.clientId = data["clientId"]
			self.channels = set(data["channels"])
	def save(self):
		data = {
			"token": self.token,
			"mode": self.mode,
			"character": self.character,
			"name": self.name,
			"clientId": self.clientId,
			"channels": list(self.channels)
		}
		with open(self.fileName, "w") as f:
			f.write(json.dumps(data, indent=2))

settings = Settings()

# Load settings or fill them in if they don't exist
if Settings.checkSettings():
	settings.load()
else:
	settings.token = input("Bot's Discord token: ")
	settings.mode = input("LLM mode (chat/chat-instruct/instruct): ")
	settings.character = input("LLM character name: ")
	settings.save()



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
		self.history.append({"role": "user", "content": msg})
		data = {
			"mode": self.mode,
			"character": self.character,
			"messages": self.history
		}
		response = api.chat(data)["message"]
		self.history.append(response)
		return response["content"]

api = API()
#chat = Chat(api, settings.mode, settings.character)
#print("Hello!")
#print(chat.reply("Hello!"))
#print("Oh, is that so?")
#print(chat.reply("Oh, is that so?"))

chats = {} # channelId: Chat



intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False

client = discord.Client(intents=intents)

@client.event
async def on_ready():
	# Update bot settings automatically
	updates = False
	if client.user.id != settings.clientId:
		settings.clientId = client.user.id
		updates = True
	if client.user.name != settings.name:
		settings.name = client.user.name
		updates = True
	if updates:
		settings.save()
	
	print(f'Logged in as {client.user}')
	print('Please be aware that character greetings are not included in the generated prompts')

def chatReply(chat, msg):
	return chat.reply(msg)

@client.event
async def on_message(message):
	# Ignore your own messages
	if message.author == client.user:
		return
	
	msg = message.clean_content
	chanId = message.channel.id
	
	# Process commands
	if msg.startswith(f"$help @{settings.name}"):
		await message.channel.send("$ping, $register, $remove, $speak")
		return
	elif msg.startswith(f"$ping @{settings.name}"):
		await message.channel.send("Pong!")
		return
	elif msg.startswith(f"$register @{settings.name}"):
		settings.channels.add(chanId)
		settings.save()
		await message.channel.send("Hello!")
		return
	elif msg.startswith(f"$remove @{settings.name}"):
		if chanId in settings.channels:
			settings.channels.remove(chanId)
			settings.save()
		await message.channel.send("Bye")
		return
	elif msg.startswith(f"$speak @{settings.name}"):
		newMsg = msg.replace(f"$speak @{settings.name}", "").strip()
		await message.channel.send(newMsg)
		return
	elif msg.startswith("$"):
		# Ignore commands that weren't for us
		return
	
	# Ignore messages from channels that we're not in
	if chanId not in settings.channels:
		return
	
	if chanId in chats:
		chat = chats[chanId]
	else:
		chat = Chat(api, settings.mode, settings.character)
		chats[chanId] = chat
	
	print(f"MSG: {msg}")
	async with message.channel.typing():
		loop = asyncio.get_event_loop()
		response = await loop.run_in_executor(None, chatReply, chat, msg)
	print(f"RESP: {response}")
	print()
	await message.channel.send(response)

client.run(settings.token)
