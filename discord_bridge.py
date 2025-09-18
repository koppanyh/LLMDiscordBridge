# Version 8 of the OpenAI-Discord bridge.
#
# This example requires the 'message_content' intent set on the bot.

from __future__ import annotations

import argparse
import asyncio
import datetime
import discord
import os
import random

from settings import Settings, DefaultFile
from api import API, Attachment, Chat, ChatRole



os.system("")  # Enables ansi escape sequences in Windows.
class Color:
    RESET   = "\x1b[m"
    BLACK   = "\x1b[30m"
    RED     = "\x1b[31m"
    GREEN   = "\x1b[32m"
    YELLOW  = "\x1b[33m"
    BLUE    = "\x1b[34m"
    MAGENTA = "\x1b[35m"
    CYAN    = "\x1b[36m"
    WHITE   = "\x1b[37m"



class Message:
	def __init__(self, message: discord.Message):
		self.channelId = message.channel.id
		self.messageId = message.id
		self.author_displayname = message.author.display_name
		self.author_username = message.author.name
		self.clean_content = message.clean_content
		self.attachments: list[Attachment] = []
		self.wall_time = datetime.datetime.now()
	async def fillAttachments(self, message: discord.Message):
		for attachment in message.attachments:
			self.attachments.append(Attachment(attachment.content_type, await attachment.read()))
	def strTime(self, cur_ts: datetime.datetime):
		wall_date = self.wall_time.date()
		date = wall_date.isoformat()
		#today = cur_ts.date()
		#if wall_date == today:
		#	date = "Today"
		#else:
		#	yesterday = cur_ts.date() - datetime.timedelta(days=1)
		#	if wall_date == yesterday:
		#		date = "Yesterday"
		return f"{date} {self.wall_time.time().isoformat(timespec='seconds')}"
	def strDelta(self, cur_ts: datetime.datetime):
		seconds = (cur_ts - self.wall_time).total_seconds()

		# Find the proper units based on the magnitude of seconds
		if seconds < 60:
			unit = "seconds"
			value = seconds
		elif seconds < 3600:  # 60 * 60
			unit = "minutes"
			value = seconds / 60
		elif seconds < 86400:  # 60 * 60 * 24
			unit = "hours"
			value = seconds / 3600
		elif seconds < 2592000:  # 60 * 60 * 24 * 30
			unit = "days"
			value = seconds / 86400
		elif seconds < 946080000:  # 60 * 60 * 24 * 365
			unit = "months"
			value = seconds / 2592000
		else:
			unit = "years"
			value = seconds / 946080000
		value = int(value)
		
		# Handle pluralization
		if value == 1:
			unit = unit[:-1]  # Remove 's' for singular form
		
		return f"{value} {unit}"
	def stringify(self, cur_ts: datetime.datetime):
		# TODO: Revert this to have delta: ({self.strDelta(cur_ts)} ago)
		return  f"**{self.author_displayname} [{self.author_username}], " \
				f"{self.strTime(cur_ts)}**\n\n{self.clean_content}"
		# Example message format:
		# ```
		# **<display name> [<username>], <date> <time> (<delta> seconds/minutes/hours ago)**
		#
		# <Message contents>
		# ```

class Conversation:
	def __init__(self, message: discord.Message, api: API):
		self.channelId = message.channel.id
		self.channel = message.channel
		self.chat = Chat(api)
		self.msg_buf: list[Message] = []
	def newMessage(self, message: discord.Message):
		msg = Message(message)
		self.msg_buf.append(msg)
		return msg
	def hasMessages(self):
		return len(self.msg_buf) > 0
	def stringify(self, cur_ts: datetime.datetime):
		if self.chat.api.settings.multiIO:
			msgs = [msg.stringify(cur_ts) for msg in self.msg_buf]
			return "\n\n-----\n\n".join(msgs)
			# Example of multi-in format:
			# ```
			# <Message payload 1>
			# 
			# -----
			# 
			# <Message payload 2>
			# 
			# -----
			# 
			# <Message payload 3>
			# ```
		else:
			return self.msg_buf.pop(0).clean_content
	def stringifyAndClear(self, cur_ts: datetime.datetime):
		msgs = self.stringify(cur_ts)
		atts = [attachment for msg in self.msg_buf for attachment in msg.attachments]
		self.msg_buf.clear()
		return msgs, atts



class Bot:
	def __init__(self, api: API):
		self.api = api
		self.conversations: dict[int, Conversation] = {}  # channelId: Conversation
		self.client: discord.Client | None = None
		self.task: asyncio.Task | None = None
	async def start(self, client: discord.Client):
		@client.event
		async def on_ready():
			self.client = client
			print(f"Logged in as {client.user}")
		
		@client.event
		async def on_message(message):
			# Ignore bot's own messages.
			if message.author == bot.getUser():
				return
			# Process any commands.
			if message.content.startswith("$"):
				return await self.processCommand(message)
			# Ignore messages from channels that we're not in.
			conversation = self.getConversation(message)
			if conversation is None:
				return
			# Process the actual messages.
			if self.api.settings.multiIO:
				await self.processMessageMulti(conversation, message)
			else:
				await self.processMessage(conversation, message)
		
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
	def getConversation(self, message: discord.Message) -> Conversation | None:
		channelId = message.channel.id
		if channelId not in self.api.settings.channels:
			# No chat if we're not registered in this channel.
			return None
		if channelId not in self.conversations:
			self.conversations[channelId] = Conversation(message, self.api)
		return self.conversations[channelId]
	async def processCommand(self, message: discord.Message):
		msg = message.content.strip()
		cmd = msg.split()
		if len(cmd) < 2:
			# Not a valid command.
			return
		is_for_me = cmd[1] == f"<@{self.getUser().id}>"
		is_for_everyone = cmd[1] == "@everyone"
		is_for_here = cmd[1] == "@here"
		if not ( is_for_me or is_for_everyone or is_for_here ):
			# Not for us.
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
			conversation = self.getConversation(message)
			if conversation is None:
				return
			conversation.chat.reset()
			await message.channel.send("$INFO: *Awakens from a coma unable to remember anything.*")
		elif cmd == "$speak":
			conversation = self.getConversation(message)
			if conversation is None:
				return
			conversation.chat.addHistory(ChatRole.ASSISTANT, msg)
			await message.channel.send(msg)
		elif cmd == "$whisper":
			conversation = self.getConversation(message)
			if conversation is None:
				return
			await message.channel.send(msg)
		elif cmd == "$die":
			await message.channel.send("$INFO: *Lays down and dies.*")
			await self.stop()
	async def processMessage(self, conversation: Conversation, message: discord.Message):
		msg = message.clean_content
		print(f"{Color.GREEN}MSG: {msg}\n({len(message.attachments)} attachments){Color.RESET}")
		atts = [Attachment(a.content_type, await a.read()) for a in message.attachments]
		response = await self.getLlmResponse(conversation, msg, atts)
		await self.respond(conversation, response)
	async def processMessageMulti(self, conversation: Conversation, message: discord.Message):
		msg = conversation.newMessage(message)
		await msg.fillAttachments(message)
		print(f"{Color.GREEN}MSG ({msg.author_displayname}): {msg.clean_content}{Color.RESET}")
		self.kickoffDelayedMessageProcessor(conversation)
	async def getLlmResponse(self, conversation: Conversation, msg: str, attachments: list[Attachment] | None = None) -> str:
		images: list[Attachment] = []
		if attachments and self.api.settings.multimodal:
			for attachment in attachments:
				if attachment.content_type.startswith("image"):
					images.append(attachment)
		async with conversation.channel.typing():
			loop = asyncio.get_event_loop()
			if images:
				response = await loop.run_in_executor(
					None,
					lambda c, m, i: c.replyWithImages(m, i),
					conversation.chat,
					msg,
					images
				)
			else:
				response = await loop.run_in_executor(
					None,
					lambda c, m: c.reply(m),
					conversation.chat,
					msg
				)
		return response
	def kickoffDelayedMessageProcessor(self, conversation: Conversation):
		if self.task is not None or not conversation.hasMessages():
			return
		# Make it faster for 1-on-1 chats
		if conversation.channel.type == discord.ChannelType.private:
			delay = random.randint(2, 5)
		else:
			delay = random.randint(3, 15)
		# TODO set the delay based on when the last one happened
		self.task = asyncio.create_task(self.delayedMessageProcessor(conversation, delay))
	async def delayedMessageProcessor(self, conversation: Conversation, delay: float):
		await asyncio.sleep(delay)
		now_ts = datetime.datetime.now()
		messages, attachments = conversation.stringifyAndClear(now_ts)
		print(f"{Color.YELLOW}MESSAGES:\n{messages}\n({len(attachments)} attachments){Color.RESET}")
		response = await self.getLlmResponse(conversation, messages, attachments)
		await self.respond(conversation, response)
		self.task = None
		self.kickoffDelayedMessageProcessor(conversation)
	async def respond(self, conversation: Conversation, response: str):
		print(f"{Color.CYAN}RESP: {response}{Color.RESET}")
		print()
		messages = response.split("\n\n-----\n\n")
		async with conversation.channel.typing():
			await self.send(conversation, messages.pop(0))
			while len(messages):
				await asyncio.sleep(1)
				await self.send(conversation, messages.pop(0))
	async def send(self, conversation: Conversation, message: str):
		# TODO split this up into multiple messages if it's over 2k bytes
		message = message.strip()
		if message == "/SKIP":
			return
		await conversation.channel.send(message)



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
