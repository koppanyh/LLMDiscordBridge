# Version 6 of the OpenAI-Discord bridge.
#
# This example requires the 'message_content' intent set on the bot.

from __future__ import annotations

import argparse
import asyncio
import discord

from settings import Settings, DefaultFile
from api import API, Chat, ChatRole



class Bot:
	def __init__(self, api):
		self.api = api
		self.chats: dict[int, Chat] = {}  # channelId: Chat
		self.client: discord.Client | None = None
	async def start(self, client: discord.Client):
		@client.event
		async def on_ready():
			self.client = client
			print(f"Logged in as {client.user}")
		@client.event
		async def on_message(message):
			await self.processMessage(message)
		await client.start(settings.token)
		#client.run(settings.token)
	async def stop(self):
		if self.client:
			print("Closing")
			await self.client.close()
			print("Closed")
	def getUser(self) -> discord.ClientUser:  # The bot's Discord user.
		if self.client is None or self.client.user is None:
			raise RuntimeError("Client user is None when it should be set")
		return self.client.user
		# self.getUser().id           - int
		# self.getUser().name         - str (username#qualifier)
		# self.getUser().display_name - str
	def getChat(self, channelId: int) -> Chat | None:
		if channelId not in self.api.settings.channels:
			# No chat if we're not registered in this channel.
			return None
		if channelId not in self.chats:
			self.chats[channelId] = Chat(self.api)
		return self.chats[channelId]
	async def processCommand(self, message: discord.Message):
		msg = message.content
		cmd = msg.split()
		if len(cmd) < 2 or cmd[1] != f"<@{self.getUser().id}>":
			# It's either not a valid command or it's not our command.
			return
		msg = msg.replace(cmd[0], "", 1).replace(cmd[1], "", 1).strip()
		cmd = cmd[0]
		channelId = message.channel.id
		
		if cmd == "$help":
			help_text = "$INFO: Format: $<cmd> @<bot> <params>\n\n" \
						"$help - List available commands\n" \
						"$ping - Test if the bot is responding\n" \
						"$register - Make the bot listen in this channel\n" \
						"$remove - Stop the bot from replying in this channel\n" \
						"$reset - Clear conversation history in this channel\n" \
						"$speak - Have the bot say something\n" \
						"$whisper - Have the bot say something without remembering it"
			await message.channel.send(help_text)
		elif cmd == "$ping":
			await message.channel.send("$INFO: Pong!")
		elif cmd == "$register":
			if channelId not in self.api.settings.channels:
				self.api.settings.channels.add(channelId)
				self.api.settings.save()
				await message.channel.send("$INFO: Hello!")
			else:
				await message.channel.send("$INFO: I'm already in this channel.")
		elif cmd == "$remove":
			if channelId in self.api.settings.channels:
				self.api.settings.channels.remove(channelId)
				self.api.settings.save()
				await message.channel.send("$INFO: Bye.")
			else:
				await message.channel.send("$INFO: I wasn't in this channel.")
		elif cmd == "$reset":
			chat = self.getChat(channelId)
			if chat is None:
				return
			chat.reset()
			await message.channel.send("$INFO: *Awakens from a coma unable to remember anything.*")
		elif cmd == "$speak":
			chat = self.getChat(channelId)
			if chat is None:
				return
			chat.addHistory(ChatRole.ASSISTANT, msg)
			await message.channel.send(msg)
		elif cmd == "$whisper":
			chat = self.getChat(channelId)
			if chat is None:
				return
			await message.channel.send(msg)
		elif cmd == "$die":
			await message.channel.send("$INFO: *lays down and dies*")
			await self.stop()
	async def processMessage(self, message: discord.Message):
		# Ignore bot's own messages.
		if message.author == bot.getUser():
			return
		
		# Process any commands.
		if message.content.startswith("$"):
			return await self.processCommand(message)
		
		chat = self.getChat(message.channel.id)
		# Ignore messages from channels that we're not in.
		if chat is None:
			return
		
		msg = message.clean_content
		print(f"MSG: {msg}")
		
		async with message.channel.typing():
			loop = asyncio.get_event_loop()
			response = await loop.run_in_executor(
				None,
				lambda c,m: c.reply(m),
				chat,
				msg
			)
		
		print(f"RESP: {response}")
		print()
		# TODO split this up into multiple messages if it's over 2k bytes
		await message.channel.send(response)



if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Discord Bridge")
	parser.add_argument(
		"--settings",
		"-s",
		default=DefaultFile, 
		help=f"Settings file [{DefaultFile}]"
	)
	args = parser.parse_args()
	
	print("Using settings file:", args.settings)
	settings = Settings(args.settings)

	api = API(settings)
	bot = Bot(api)
	
	intents = discord.Intents.default()
	intents.message_content = True
	intents.typing = False
	intents.presences = False
	
	client = discord.Client(intents=intents)

	asyncio.run(bot.start(client))
