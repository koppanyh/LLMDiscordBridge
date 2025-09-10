# LLMDiscordBridge

A simple app that exposes an OpenAI-like LLM API to be used to drive a Discord bot.

This is primarily designed to interface with `llama-server` from the [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) project.

## Usage

Run `python discord_bridge.py` to run the bridge. An optional `-s <file>` parameter can be used to specify a settings file to load besides the default `settings.json`.

The bot can be configured to listen for messages on specific channels of a server and reply to them.

Calling `$register @Bot` (where @Bot is the bot's Discord name) will tell it what channel to listen and reply to.

Bots will ignore commands for other bots.

### Bot Commands

- `$help @Bot` Used to list out these commands
- `$ping @Bot` Used to get the bot to reply "Pong!" to test that it can read and write on a channel
- `$register @Bot` Used to make the bot listen and reply to messages on a channel
- `$remove @Bot` Remove the bot from a channel so it doesn't reply to any messages
- `$reset @Bot` Clear the bot's memory of that channel's conversation
- `$speak @Bot` Used to make the bot say something to initiate conversations
- `$whisper @Bot` Used to make the bot say something without remembering it

## Setup

### Discord Bot

- [Set up a Discord bot](https://discordpy.readthedocs.io/en/stable/discord.html) if you don't have one already
- Make sure the `Message Content Intent` checkbox is set to true
- Add it to the server of your choice, make sure it has message read and write permissions

### Llama Server

Llama Server needs to be started with a command similar to the following:
```
llama-server.exe -ngl 9999 --host 0.0.0.0 -dev CUDA0 --jinja -c 42000 -m Qwen3-30B-A3B-Thinking-2507-Q4_K_S.gguf
```

### First Time

- Activate your Python environment if needed
- Run `python -m pip install -U discord.py` to install the Discord library
- Run `python discord_bridge.py` to run the bridge
- You will be asked to fill in some info
  - Token: the token of the bot, used to authenticate with Discord
  - URL: the URL to the LLM's OpenAI-like API, default `http://localhost:8080` (no slash at the end)
  - Prompt: the system prompt to configure how your bot will act
  - LLM API Token: the token of the LLM's API, used to authenticate with OpenRouter or other API providers (optional)
- These settings will be saved to `settings.json` if you need to change it later

### Manual settings.json

The `settings.json` can be manually updated for advanced config.

 - token: Discord bot token
 - url: LLM API endpoint URL (default: `http://localhost:8080`, gets `/v1/chat/completions` added to it internally)
 - prompt: System prompt for the LLM
 - promptFile: Path to a file containing the system prompt (optional, overwrites contents of `prompt`)
 - channels: List of registered channel IDs (automatically managed)
 - apiParams: Dictionary of LLM API parameters to override defaults (optional)
   - e.g. `"temperature": 0.6`
   - e.g. `"top_p": 0.9`
   - e.g. `"model": "deepseek/deepseek-chat-v3-0324"` (used for OpenRouter.ai)
 - llmToken: LLM's API authentication token (optional)
 - ~~tools: tool configs that the bot is allowed to use~~ (not implmented)
