# MinecraftServerStatus-Discord
In a Discord embed, shows the status of a Minecraft server.


## Config example

In a `config.json` file, store the following settings:

```
{
  "server_address": "server.address.ext",
  "discord_bot_token": "yoursuperSicretToken",
  "discord_channel_id": 0
}
```

* `server_address`: The address (or IP address) of your Minecraft server;
* `discord_bot_token`: A token you'll get from [Discord](https://discord.com/developers/applications/);
* `discord_channel_id`: The ID of the channel in which the bot will show the server status (make sure the bot has the right to write and use embeds in that channel).
* `show_user_list`: If `true`, shows a list of connected users.
