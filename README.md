[![DiscordBot](https://img.shields.io/badge/Discord%20Bot-Invite-blueviolet)](https://discord.com/api/oauth2/authorize?client_id=701526567763050517&permissions=379968&redirect_uri=https%3A%2F%2Fkabyle-gamers.com%2Fminecraft&scope=bot)
[![Donate](https://img.shields.io/badge/Donate-Jahus-ff69b4)](https://www.patreon.com/jahus)

[![Discord](https://img.shields.io/discord/764789719032266752?label=Kabyle%20Minecraft%20on%20Discord)](https://discord.gg/PMHuPpD)

# MinecraftServerStatus-Discord
> In a Discord embed, shows the status of a Minecraft server.

## Usage

* `mc/link <server> [showUsers]`
  > Link your Minecraft Server to your Discord Guild. The status will be shown in the same channel where you have sent the command.
  > `<server>`: The address of your Minecraft Server in the form `sub.domain.ext` or `domain.ext`.
  > `[showUsers]`: Optional. `True` or `False` (default). Whether to show the list of connected players. Don't set to `True` on massive servers.
* `mc/unlink`
  > Stop receiving updates about the Minecraft Server and delete the status message.

**Notes**

1. Only one Minecraft Server can be linked to a Discord Guild. Using `mc/link` again will overrite whatever settings you have previously applied.
1. The bot has been made to minimize interactions and messages. By design, it will not message you if something is wrong. If the status message is not updating, please make sure you have correctly used the `mc/link` command. Try again if you are unsure.
1. In case something is going wrong, have found a bug or have you a suggestion to make, you might contact me on Discord (`Jahus#9238`) or [Telegram](https://t.me/Jahus).
1. If the bot is useful, consider making a donation [on Patreon](https://www.patreon.com/jahus).

## Self-hosting

Prepare a channel for people to check your Minecraft Server status. Make it so only the bot can send messages there. Once the first status message is sent, the bot will update it every 5 minutes. Please, don't try to change the update time to less than 60 seconds; the API won't update its cache that fast.

Want to self-host the bot? Create a Discord Bot on the [Discord Developer Dashboard](https://discord.com/developers/applications/). Once done, get your token and set it in the `config.json` file.

### Config example

In a `config.json` file, store the following settings:

```
{
  "server_address": "server.address.ext",
  "discord_bot_token": "yoursuperSicretToken",
  "discord_channel_id": 0,
  "show_user_list": false
}
```

* `server_address`: The address (or IP address) of your Minecraft server;
* `discord_bot_token`: A token you'll get from [Discord](https://discord.com/developers/applications/);
* `discord_channel_id`: The ID of the channel in which the bot will show the server status (make sure the bot has the right to write and use embeds in that channel).
* `show_user_list`: If `true`, shows a list of connected users (you might keep it `false` if you have many users who connect at the same time).

### Running as a service

To run the bot at your server's startup, register the `.service` file with `systemctl` and enable it.

## Minecraft Server Status
This bot uses the [Minecraft Server Status API](https://mcsrvstat.us/), that's completely free. If you appreciate their work, consider [donating to them on PayPal](https://www.paypal.com/paypalme/spirit55555).
