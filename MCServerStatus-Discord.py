import discord, json, requests, time, emoji, datetime


with open("config.json", "r") as _f:
    config = json.loads(_f.read())


__token= config["discord_bot_token"]
__sleep_time = 60
__client = discord.Client()
__colors = {
    "online": 0x00ff00,
    "offline": 0xff0000
}


@__client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(__client))
    await test()


async def test():
    _embed_message = None
    while True:
        _req = requests.get("https://api.mcsrvstat.us/2/mcj.kabyle-gamers.com")
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
                if _req_json["players"]["online"] > 0:
                    _server_data["Liste des héros présents"] = "\n• %s" % "\n• ".join(_req_json["players"]["list"])
                for _key in _server_data:
                    _embed.add_field(
                        name=_key,
                        value=_server_data[_key],
                        inline=False
                    )
            _embed.add_field(
                name="Dernière mise à jour",
                value="%s `%s`" % (emoji.emojize(":clock1:"),datetime.datetime.strftime(datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=1))), "%H:%M:%S"))
            )
            if not _embed_message:
                try:
                    _channel = __client.get_channel(config["discord_channel_id"])
                    _embed_message = await _channel.send(embed=_embed)
                except:
                    print("Error: Could not send message to channel.")
            else:
                try:
                    await _embed_message.edit(embed=_embed)
                except discord.errors.NotFound:
                    _embed_message = None
        time.sleep(__sleep_time)


__client.run(__token)
