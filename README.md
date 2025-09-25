[![Donate](https://img.shields.io/badge/Donate-Jahus-ff69b4)](https://www.patreon.com/jahus)

# MinecraftServerStatus-Discord
> In a Discord embed, shows the status of a Minecraft server.

## Usage

* `/link`
  > Link your Minecraft Server to your Discord Guild. The status message will be shown in the same channel where you have sent the command. You can choose a separate channel for server IP.
* `/unlink`
  > Stop receiving updates about the Minecraft Server. You can choose to delete the status messages.

### Parameters
* `server_address`: Required. Can be either:
  * A plain IP or hostname, with optional port. Example: `mc.mydomain.com`, `mc.mydomain.com:25569`, `69.543.8.12:25569`.
  * `auto`, with optional port. Example: `auto` or `auto:25569`. The script will automatically resolve your external IP.
  * `file`, with optional port.</br>The script will get your hostname or IP from the file defined in `server_address_file`.</br>Example: `"server_address": "file:25565"`
* `server_address_file`: Required if `server_address` is defined to `file`.</br>Path to a file containing a single line with the IP or hostname. Might contain a port number. Environment variables are supported.</br>Example: `"server_address_file": "$HOME/mcserver/ngrok.txt"`, where `ngrok.txt` contains `something.ngrok.io`.
* `change_channel_name`: Optional. Default: `False`. Change the name of the channel where the status message is sent. Default names are `🟩-online` and `🟥-offline`.
* `channel_name_online`: Optional. Default: `🟩-online`. Name of the status channel when the server is online.
* `channel_name_offline`: Optional. Default: `🟥-offline`. Name of the status channel when the server is offline.
* `show_player_list`: Optional. Default: `True`. Show a list of all the connected players in the status message.
* `show_ip`: Optional. Default: `True`. Show server IP in the status message. You can hide the IP and show it in a different channel. Useful if your server is invite-only, but you still want other members to see its status and active players.
* `ip_update_channel`: Optional. Channel where the IP address will be sent. Use channel ID (right click on channel > Copy Channel ID if Developer Mode is active).
* `default_server_name`: Optional. Title for the status message.
* `use_motd_as_default_server_name`: Optional. Default: `False`. Use MOTD as title instead of server name.


**Notes**

1. You need `Administrator` permission in order to use this bot in your server.
1. Only one Minecraft Server can be linked to a Discord Guild. Using `/link` again will overwrite whatever settings you have previously applied.
1. The bot has been made to minimize interactions and messages. By design, it will not message you if something is wrong (can't send message, can't reach the Minecraft Server, if you don't have the required permissions, etc.). If the status message is not updating, please make sure you have correctly used the `/link` command. Try again if you are unsure.
1. In case something is going wrong, have found a bug or have you a suggestion to make, you might contact me on Discord (`@Jahus`) or [Telegram](https://t.me/DarthJahus).
1. If the bot is useful, consider making a donation [on Patreon](https://www.patreon.com/jahus).

## Self-hosting

Prepare a channel for people to check your Minecraft Server status. Make it so only the bot can send messages there. Once the first status message is sent, the bot will update it every 5 minutes. Please, don't try to change the update time to less than 60 seconds; the API won't update its cache that fast.

Want to self-host the bot? Create a Discord Bot on the [Discord Developer Dashboard](https://discord.com/developers/applications/). Once done, get your token and set it in the `config.json` file.

### Config

In a `config.json` file, store the following settings:

```
{
  "discord_bot_token": "sicret.token.w-o-w",
  "sleep_time": 300
}
```

* `discord_bot_token`: A token you'll get from [Discord](https://discord.com/developers/applications/);
* `sleep_time`: Time between server status updates. Keep it above 60 s.

### Running as a service
To run the bot at your server's startup, register the `.service` file with `systemctl` and enable it.

## Minecraft Server Status
This bot uses the [Minecraft Server Status API](https://mcsrvstat.us/), that's completely free. If you appreciate their work, consider [donating to them on PayPal](https://www.paypal.com/paypalme/spirit55555).

## Contributions
Feel free to build upon the actual code.
