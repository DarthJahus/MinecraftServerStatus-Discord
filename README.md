[![Discord](https://img.shields.io/discord/764789719032266752?label=Kabyle%20Minecraft%20on%20Discord)](https://discord.gg/PMHuPpD)

# MinecraftServerStatus-Discord
> In a Discord embed, shows the status of a Minecraft server.

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
