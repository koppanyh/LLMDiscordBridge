# Version 7 of the OpenAI-Discord bridge.
#
# This example requires the 'message_content' intent set on the bot.

from __future__ import annotations

import argparse
import asyncio
import datetime
import discord

from settings import Settings, DefaultFile
from api import API, Chat, ChatRole



class Message:
	def __init__(self, message: discord.Message):
		self.channelId = message.channel.id
		self.messageId = message.id
		self.author_name = message.author.display_name
		self.clean_content = message.clean_content
		self.wall_time = datetime.datetime.now()
	def strTime(self, cur_ts: datetime.datetime):
		wall_date = self.wall_time.date()
		today = cur_ts.date()
		if wall_date == today:
			date = "Today"
		else:
			yesterday = cur_ts.date() - datetime.timedelta(days=1)
			if wall_date == yesterday:
				date = "Yesterday"
			else:
				date = wall_date.isoformat()
		# TODO: remove this line to get relative dates back
		date = wall_date.isoformat()
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
		
		return f"{value} {unit} ago"
	def stringify(self, cur_ts: datetime.datetime):
		# TODO: Revert this to have delta
		#return  f"**{self.author_name}, {self.strTime(cur_ts)} ({self.strDelta(cur_ts)})**" \
		return  f"**{self.author_name}, {self.strTime(cur_ts)}**" \
				f"\n\n{self.clean_content}"
		# Example message format:
		# ```
		# **<username>, <date> <time> (<delta> seconds/minutes/hours ago)**
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
			# **<Username A>, <time> (<delta> seconds/minutes/hours ago)**
			#
			# <Message contents>
			# 
			# -----
			# 
			# **<Username B>, <time> (<delta> seconds/minutes/hours ago)**
			#
			# <Message contents>
			# 
			# -----
			# 
			# **<Username C>, <time> (<delta> seconds/minutes/hours ago)**
			#
			# <Message contents>
			# ```
		else:
			return self.msg_buf.pop(0).clean_content
	def stringifyAndClear(self, cur_ts: datetime.datetime):
		msgs = self.stringify(cur_ts)
		self.msg_buf.clear()
		return msgs



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
		print(f"MSG: {msg}")
		response = await self.getLlmResponse(conversation, msg)
		await self.respond(conversation, response)
	async def processMessageMulti(self, conversation: Conversation, message: discord.Message):
		msg = conversation.newMessage(message)
		print(f"MSG ({msg.author_name}): {msg.clean_content}")
		self.kickoffDelayedMessageProcessor(conversation)
	async def getLlmResponse(self, conversation: Conversation, msg: str) -> str:
		async with conversation.channel.typing():
			loop = asyncio.get_event_loop()
			response = await loop.run_in_executor(
				None,
				lambda c,m: c.reply(m),
				conversation.chat,
				msg
			)
		return response
	def kickoffDelayedMessageProcessor(self, conversation: Conversation):
		if self.task is None and conversation.hasMessages():
			# TODO set the delay based on when the last one happened
			self.task = asyncio.create_task(self.delayedMessageProcessor(conversation, 10))
	async def delayedMessageProcessor(self, conversation: Conversation, delay: float):
		await asyncio.sleep(delay)
		now_ts = datetime.datetime.now()
		messages = conversation.stringifyAndClear(now_ts)
		print(f"MESSAGES:\n{messages}")
		response = await self.getLlmResponse(conversation, messages)
		await self.respond(conversation, response)
		self.task = None
		self.kickoffDelayedMessageProcessor(conversation)
	async def respond(self, conversation: Conversation, response: str):
		print(f"RESP: {response}")
		print()
		# TODO split this up into multiple messages if it's over 2k bytes
		# TODO split this up into multiple messages if it's a multi output
		await conversation.channel.send(response)



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
