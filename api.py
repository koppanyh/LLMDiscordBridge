# Version 2 of the OpenAI API interface.

import base64
import requests

from enum import Enum
from settings import Settings


class API:
	headers = {
		"Content-Type": "application/json"
	}
	def __init__(self, settings):
		self.settings = settings
		self.url = f"{settings.url}/v1/chat/completions"
	def chat(self, data):
		response = requests.post(
			self.url,
			headers=API.headers,
			json=data,
			verify=False
		)
		#print(response.content)
		try:
			return response.json()["choices"][0]
			# {'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': "Hey! What's up?"}}
		except Exception as e:
			print(response.content)
			raise e


class ChatRole(Enum):
    SYSTEM    = "system"
    ASSISTANT = "assistant"
    USER      = "user"
    TOOL      = "tool"

class Chat:
	def __init__(self, api, auto_prompt=True):
		self.api = api
		self.history = []
		if auto_prompt and api.settings.prompt:
			self.addHistory(ChatRole.SYSTEM, api.settings.prompt)
	def rawReply(self, messages, use_tools=False):
		#print("\t", messages)
		# TODO: Maybe add these parameters into the settings?
		data = {
			"messages": messages,
			"stream": False,
			"cache_prompt": True,
			"samplers": "edkypmxt",
			"temperature": 0.8,
			"dynatemp_range": 0,
			"dynatemp_exponent": 1,
			"top_k": 40,
			"top_p": 0.95,
			"min_p": 0.05,
			"typical_p": 1,
			"xtc_probability": 0,
			"xtc_threshold": 0.1,
			"repeat_last_n": 64,
			"repeat_penalty": 1,
			"presence_penalty": 0,
			"frequency_penalty": 0,
			"dry_multiplier": 0,
			"dry_base": 1.75,
			"dry_allowed_length": 2,
			"dry_penalty_last_n": -1,
			"max_tokens": -1,
			"timings_per_token": False
		}
		# TODO: Tool calling will be implemented later
		# if use_tools:
		# 	data["tools"] = [
		# 		{
		# 			"type": "function",
		# 			"function": {
		# 				"name": "calculate",
		# 				"description": "Evaluate a mathematical expression",
		# 				"parameters": {
		# 					"type": "object",
		# 					"properties": {
		# 						"expression": {
		# 							"type": "string",
		# 							"description": "The mathematical expression to evaluate",
		# 						}
		# 					},
		# 					"required": ["expression"],
		# 				}
		# 			}
		# 		}
		# 	]
		# 	data["tool_choice"] = "auto"
		resp = self.api.chat(data)
		#print(resp)
		return resp
	def reply(self, msg, use_tools=False):
		self.addHistory(ChatRole.USER, msg)
		response = self.rawReply(self.history, use_tools)["message"]
		self.history.append(response)
		# TODO: Implement tool calling functionality later
		# if response.get("tool_calls"):
		#     for tool_call in response["tool_calls"]:
		#         func = tool_call["function"]
		#         self.addHistory(
		#             ChatRole.TOOL,
		#             calculate(**json.loads(func["arguments"])),
		#             name=func["name"],
		#             tool_call_id=tool_call["id"]
		#         )
		#     #self.printHistory()
		#     response = self.rawReply(self.history, False)["message"]
		#     self.history.append(response)
		return response["content"]
	def replyWithImage(self, msg, img_path, use_tools=False):
		img_ext = img_path.split('.')[-1].lower()
		mimes = {
			"jpg": "jpeg",
			"jpeg": "jpeg",
			"png": "png"
		}
		if (img_ext not in mimes):
			raise ValueError("Invalid image extension")
		img_ext = mimes[img_ext]
		with open(img_path, "rb") as image_file:
			base64_image = base64.b64encode(image_file.read()).decode("utf-8")
		return self.reply([
			{
				"type": "text",
				"text": msg
			},
			{
				"type": "image_url",
				"image_url": {
					"url": f"data:image/{img_ext};base64,{base64_image}"
				}
			}
		], use_tools)
	def addHistory(self, role: ChatRole, content, **args):
		args["role"] = role.value
		args["content"] = content
		self.history.append(args)


if __name__ == "__main__":
	# Demo of the API

	settings = Settings()
	api = API(settings)
	chat = Chat(api)

	while True:
		msg = input("> ")
		if msg == "/exit":
			break
		print("\t" + chat.reply(msg).replace("\n", "\n\t"))
