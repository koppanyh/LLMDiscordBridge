# LLMDiscordBridge

A bridge for oobabooga/text-generation-webui and Discord, using the OpenAI API format.

## Usage

The bot can be configured to listen for messages on specific channels of a server and reply to them.

Calling `$register @Bot` (where @Bot is the bot's Discord name) will tell it what channel to listen and reply to.

Bots will ignore commands for other bots.

### Commands
- `$help @Bot` Used to list out these commands
- `$ping @Bot` Used to get the bot to reply "Pong!" to test that it can read and write on a channel
- `$register @Bot` Used to make the bot listen and reply to messages on a channel
- `$remove @Bot` Remove the bot from a channel so it doesn't reply to any messages
- `$speak @Bot` Used to make the bot say something to initiate conversations

## Setup

Discord bot:
- [Set up a Discord bot](https://discordpy.readthedocs.io/en/stable/discord.html) if you don't have one already
- Make sure the Message Content Intent checkbox is set to true
- Add it to the server of your choice, make sure it has message read and write permissions

First time:
- Activate your Python environment if needed
- Run `python -m pip install -U discord.py` to install the Discord library
- Run `python discord_bridge.py` to run the bridge
- You will be asked to fill in some info
  - Token: the token of the bot, used to authenticate with Discord
  - Mode: the chat mode, as found in the Text Generation UI's chat mode selector
  - Character: the character to use, as found in the Text Generation UI's character gallery
- These settings will be saved to `discord_settings.json` if you need to change it later

The Text Generation UI needs to be started with the `--listen --api` flags in order for this to work.
