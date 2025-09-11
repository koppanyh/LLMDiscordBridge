# Version 5 of the settings interface.

import json

DefaultURL  = "http://localhost:8080"
DefaultFile = "settings.json"

class Settings:
	def __init__(self, file_name=DefaultFile, auto_load=True):
		# Saved settings
		self.token = ""
		self.url = DefaultURL
		self.prompt = ""
		self.promptFile = ""  # This overwrites prompt.
		self.channels = set()
		self.apiParams = {}
		self.llmToken = ""
		self.multiIO = False
		# Runtime settings
		self.file_name = file_name
		self.prompt_from_file = ""
		if auto_load:
			self.loadSafe()
	def load(self):
		with open(self.file_name, "r") as f:
			data = {
				"token": self.token,
				"url": self.url,
				"prompt": self.prompt,
				"promptFile": self.promptFile,
				"channels": list(self.channels),
				"apiParams": self.apiParams,
				"llmToken": self.llmToken,
				"multiIO": self.multiIO
			}
			data.update(json.loads(f.read()))
			self.token = data["token"]
			self.url = data["url"]
			self.prompt = data["prompt"]
			self.promptFile = data["promptFile"]
			self.channels = set(data["channels"])
			self.apiParams = data["apiParams"]
			self.llmToken = data["llmToken"]
			self.multiIO = data["multiIO"]
			if self.promptFile:
				try:
					with open(self.promptFile, "r") as f:
						self.prompt_from_file = f.read()
				except FileNotFoundError:
					print(f"ERROR: {self.promptFile} not found, defaulting to standard prompt!")
	def save(self):
		data = {
			"token": self.token,
			"url": self.url,
			"prompt": self.prompt,
			"promptFile": self.promptFile,
			"channels": list(self.channels),
			"apiParams": self.apiParams,
			"llmToken": self.llmToken,
			"multiIO": self.multiIO
		}
		with open(self.file_name, "w") as f:
			f.write(json.dumps(data, indent=2))
	def loadSafe(self):
		# Load settings or fill them in if we can't.
		try:
			self.load()
		except FileNotFoundError:
			self.token = input("Bot's Discord token: ")
			self.url = input(f"OpenAI API endpoint [{DefaultURL}]: ")
			if not self.url:
				self.url = DefaultURL
			self.prompt = input("Prompt to use for the LLM: ")
			self.llmToken = input("LLM API token (optional): ")
			self.save()
	def getPrompt(self):
		if self.prompt_from_file:
			return self.prompt_from_file
		return self.prompt
