#!/usr/bin/python3

import discord, json, requests, time, emoji, datetime


with open("config.json", "r") as _f:
    config = json.loads(_f.read())


__token= config["discord_bot_token"]
__sleep_time = 300
__client = discord.Client()
__colors = {
    "online": 0x00ff00,
    "offline": 0xff0000
}


@__client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(__client))
    await mc_server_status()


async def mc_server_status():
    try:
        with open("last_message.id", "r") as _f:
            _embed_message_id = int(_f.read())
    except:
        _embed_message_id = -1
    while True:
        _req = requests.get("https://api.mcsrvstat.us/2/%s" % config["server_address"])
        if _req.status_code != 200:
            print("Error contacting API : %s" % _req.status_code)
        else:
            _req_json = _req.json()
            if not _req_json["online"]:
                _embed = discord.Embed(
                    title="Kabyle Minecraft",
                    color=__colors["offline"]
                )
                _embed.add_field(
                    name="État",
                    value="%s Hors ligne" % emoji.emojize(":red_circle:"),
                    inline=False
                )
            else:
                _embed = discord.Embed(
                    title="Kabyle Minecraft",
                    color=__colors["online"]
                )
                _server_data = {
                    "État": "%s En ligne" % emoji.emojize(":green_circle:"),
                    "Motd": "%s %s" % (emoji.emojize(":speech_balloon:"), _req_json["motd"]["clean"][0]),
                    "Version": "%s `%s`" % ("<:mc_grass:764825467425128478>", _req_json["version"]),
                    "Héros": "%s `%i / %i`" % ("<:steve_cool:764829193073983519>", _req_json["players"]["online"],_req_json["players"]["max"]),
                    "IP actuelle": "%s `%s`" % (emoji.emojize(":desktop:"), _req_json["ip"])
                }
                if config["show_user_list"] and _req_json["players"]["online"] > 0:
                    _server_data["Liste des héros présents"] = "\n• %s" % "\n• ".join(_req_json["players"]["list"])
                for _key in _server_data:
                    _embed.add_field(
                        name=_key,
                        value=_server_data[_key],
                        inline=False
                    )
            _embed.add_field(
                name="Dernière mise à jour",
                value="%s `%s`" % (emoji.emojize(":arrows_counterclockwise:"),datetime.datetime.strftime(datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=1))), "%H:%M:%S"))
            )
            if _embed_message_id == -1:
                try:
                    _channel = __client.get_channel(config["discord_channel_id"])
                    _embed_message = await _channel.send(embed=_embed)
                    _embed_message_id = _embed_message.id
                except:
                    print("Error: Could not send message to channel.")
            else:
                try:
                    _channel = __client.get_channel(config["discord_channel_id"])
                    _embed_message = await _channel.fetch_message(_embed_message_id)
                    await _embed_message.edit(embed=_embed)
                except discord.errors.NotFound:
                    _embed_message_id = -1
                except discord.errors.Forbidden:
                    # You do not have the permissions required to get a message.
                    print("Error: Please, allow the bot to view ancient messages.")
                    _embed_message_id = -1
            with open("last_message.id", "w") as _f:
                _f.write(str(_embed_message_id))
        time.sleep(__sleep_time)


__client.run(__token)
